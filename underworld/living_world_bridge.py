"""Copy-only integration of the G01/G47/L02/L59/M03/M48 foundations.

The native UW10W/life world remains authoritative for bodies, time, resources,
actions, weather and receipts.  This module adds one transactional bridge row to
an explicit copy of that world and advances the six JSON foundations from
native observations.  It never writes the source database and it never lets a
foundation sidecar execute a native action.

The bridge deliberately uses the existing ``life_store`` transaction helpers
inside one SQLite transaction.  That keeps a native life operation and the
matching sidecar checkpoint in the same commit boundary while leaving the
historical life store schema and source registration untouched.
"""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

from . import lifecycle_l02 as l02
from . import lifecycle_l59 as l59
from . import life_store
from . import micro_ecology_m03 as m03
from . import micro_ecology_m48 as m48
from . import plant_underground_g47 as g47
from . import weather_store as weather
from . import world_generation_g01 as g01
from .lease import Lease


RULE = "alice-living-world-bridge-1"
SCHEMA = "alice-living-world-bridge/v1"
VERSION = 1
MAX_OPERATIONS = 4096
MAX_OPERATION_ID = 64
EMPTY_HASH = hashlib.sha256(b"{}").hexdigest()
TABLES = ("living_bridge_meta", "living_bridge_state", "living_bridge_operations")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _loads(value: str) -> Any:
    return json.loads(value)


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_hash(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _state_hash(state: Mapping[str, Any]) -> str:
    body = deepcopy(dict(state))
    body.pop("state_hash", None)
    return _hash_text(_dumps(body))


def _finite(value: Any, label: str, low: float | None = None,
            high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if low is not None and result < low or high is not None and result > high:
        raise ValueError(f"{label} is outside its bounds")
    return result


def _copy_database(source: str | Path, destination: str | Path) -> str:
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("source living world does not exist")
    if destination.exists():
        raise FileExistsError("living-world attach requires a NEW destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
            with closing(sqlite3.connect(destination)) as target:
                origin.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("living-world destination backup integrity check failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if _file_hash(source) != source_hash:
        raise ValueError("source living world changed during attach")
    return source_hash


def _has_tables(path: str | Path, names: set[str]) -> bool:
    path = Path(path).resolve()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        found = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN (%s)"
                % ",".join("?" for _ in names), tuple(sorted(names))
            )
        }
    return found == names


def _projection_climate(climate: Mapping[str, Any]) -> dict[str, Any]:
    current = climate.get("current", {}) if isinstance(climate, Mapping) else {}
    return {
        "season": climate.get("season", "unknown"),
        "weather": climate.get("weather", "clear"),
        "ambient_c": float(climate.get("ambient_c", 15.0)),
        "daylight_factor": float(climate.get("daylight_factor", 0.5)),
        "growth_factor": float(climate.get("growth_factor", 1.0)),
        "rain_mm_h": float(current.get("rain_mm_h", 0.0)),
        "cloud_fraction": float(current.get("cloud_fraction", 0.0)),
        "wind_m_s": [float(v) for v in current.get("wind_m_s", (0.0, 0.0))],
    }


def _projection_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    allowed_kinds = {"actor", "tree", "resource", "animal", "forage"}
    entities = []
    for entity in snapshot.get("entities", []):
        if entity.get("kind") not in allowed_kinds:
            continue
        copy_entity = {
            key: deepcopy(entity[key])
            for key in (
                "entity_id", "kind", "position_m", "mass_kg", "stage", "alive",
                "condition", "body", "inventory_ug", "present",
            ) if key in entity
        }
        entities.append(copy_entity)
    entities.sort(key=lambda item: item["entity_id"])
    return {
        "run_id": str(snapshot.get("run_id", "")),
        "tick": int(snapshot.get("tick", 0)),
        "simulated_time_s": float(snapshot.get("simulated_time_s", 0.0)),
        "dt_s": float(snapshot.get("dt_s", 0.25)),
        "seed": int(snapshot.get("seed", 0)),
        "world_bounds_m": deepcopy(snapshot.get("world_bounds_m", {"width": 32.0, "height": 32.0})),
        "entities": entities,
    }


def _native_projection(world: Any) -> dict[str, Any]:
    snapshot = world.snapshot()
    return {
        "snapshot": _projection_snapshot(snapshot),
        "climate": _projection_climate(world.weather_snapshot()),
    }


def _projection_hash(projection: Mapping[str, Any]) -> str:
    return _hash_text(_dumps(projection))


def _entities(projection: Mapping[str, Any], kind: str) -> list[dict[str, Any]]:
    return [deepcopy(entity) for entity in projection["snapshot"]["entities"]
            if entity.get("kind") == kind]


def _actor_ids(projection: Mapping[str, Any]) -> list[str]:
    return sorted(entity["entity_id"] for entity in _entities(projection, "actor"))


def _tree_ids(projection: Mapping[str, Any]) -> list[str]:
    return sorted(entity["entity_id"] for entity in _entities(projection, "tree"))


def _native_seed(projection: Mapping[str, Any]) -> int:
    return int(projection["snapshot"].get("seed", 0))


def _world_config(projection: Mapping[str, Any]) -> dict[str, Any]:
    bounds = projection["snapshot"].get("world_bounds_m", {})
    width_m = max(4.0, float(bounds.get("width", 32.0)))
    height_m = max(4.0, float(bounds.get("height", 32.0)))
    # Keep the adapter bounded while still covering the complete native area.
    # A 32m native world therefore maps to an 8x8 G01 grid at 4m per cell.
    cell_scale_m = max(0.25, min(10.0, max(width_m, height_m) / 8.0))
    width = max(4, min(64, int(math.ceil(width_m / cell_scale_m))))
    height = max(4, min(64, int(math.ceil(height_m / cell_scale_m))))
    return g01.preset_config(
        "temperate_woodland_meadow",
        width=width,
        height=height,
        cell_scale_m=cell_scale_m,
        starting_population=0,
        mode="research",
    )


def _coord_for_entity(entity: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[int, int]:
    position = entity.get("position_m", (0.0, 0.0))
    width = int(manifest["config"]["width"])
    height = int(manifest["config"]["height"])
    scale = float(manifest["config"].get("cell_scale_m", 1.0))
    return (
        max(0, min(width - 1, int(round(float(position[0]) / scale)))),
        max(0, min(height - 1, int(round(float(position[1]) / scale)))),
    )


def _native_tree_species(entity: Mapping[str, Any]) -> str:
    # Native UW10W exposes trees but not G47 species IDs.  This is a declared
    # adapter mapping, not a claim that native tree taxonomy is complete.
    return "sunspire_tree" if entity.get("stage") in {"mature", "old"} else "shelter_brush"


def _add_native_trees(state: dict[str, Any], projection: Mapping[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, entity in enumerate(_entities(projection, "tree")):
        native_id = str(entity["entity_id"])
        plant_id = f"native-plant-{native_id}"
        species_id = _native_tree_species(entity)
        coord = _coord_for_entity(entity, state["source_cells_manifest"])
        traits = state["species_catalog"][species_id]
        biomass = max(0.01, min(float(traits["max_biomass_kg"]), float(entity.get("mass_kg", 0.01))))
        adult = entity.get("stage") in {"mature", "old"}
        age = float(traits["mature_days"]) if adult else float(traits["mature_days"]) * 0.5
        state["plants"].append({
            "plant_id": plant_id,
            "species_id": species_id,
            "coord": {"x": coord[0], "y": coord[1]},
            "stage": "adult" if adult else "juvenile",
            "age_days": round(age, 8),
            "biomass_kg": round(biomass, 8),
            "reserve_kg": round(biomass * float(traits["root_reserve_fraction"]), 8),
            "seed_supply": 0,
            "flowered": False,
            "pollinated": False,
            "alive": bool(entity.get("alive", True)),
            "stump": False,
            "individual_index": index,
        })
        mapping[native_id] = plant_id
    state.pop("source_cells_manifest", None)
    state["state_hash"] = g47.state_hash(state)
    return mapping


def _traits_from_actor(entity: Mapping[str, Any]) -> dict[str, float]:
    body = entity.get("body", {})
    health = max(0.0, min(1.0, float(body.get("health", 1.0))))
    hunger = max(0.0, min(1.0, float(body.get("hunger", 0.35))))
    fatigue = max(0.0, min(1.0, float(body.get("fatigue", 0.2))))
    return {
        "body_size_potential": 0.5,
        "metabolic_efficiency": round(0.5 + 0.5 * health, 6),
        "maturation_tendency": round(0.5 + 0.25 * (1.0 - fatigue), 6),
        "sensory_sensitivity": round(0.5 + 0.25 * (1.0 - hunger), 6),
    }


def _initial_l02(projection: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    state = l02.initial_state(run_id)
    resident = l02.life_stage("resident", 0, None, False, {"native_observation": True})
    profile = l02.reproductive_profile(
        "native-none", "native_actor", "none", ["none"], "resident", 0,
        {"food": 0.0}, conception_probability=0.0, reproductive_system="none",
    )
    contract = l02.species_lifecycle("native_actor", [resident], [profile])
    l02.register_species(state, contract)
    for entity in _entities(projection, "actor"):
        ident = entity["entity_id"]
        l02.add_individual(state, {
            "id": ident,
            "species_id": "native_actor",
            "age_steps": 0,
            "stage_id": "resident",
            "biological_role": "none",
            "gender_identity": "unknown",
            "reproductive_profile_id": "native-none",
            "alive": bool(entity.get("alive", True)),
            "traits": _traits_from_actor(entity),
            "resources": {"food": 0.0, "water": 0.0},
            "knowledge": [],
            "lexicon": [],
            "relationship_ids": [],
        })
    l02.validate_state(state)
    return state


def _initial_l59(projection: Mapping[str, Any], run_id: str) -> dict[str, Any]:
    state = l59.initial_state(
        run_id,
        seed=_native_seed(projection),
        carrying_capacity=len(_entities(projection, "actor")),
    )
    resident = l59.life_stage(
        "resident", 0, None, False, {"native_observation": True},
        function_scale=1.0, care_needs={}, deprivation_tolerance=0,
        mortality_hazard=0.0,
    )
    l59.register_species(state, "native_actor", [resident], max_age_steps=None)
    for entity in _entities(projection, "actor"):
        ident = entity["entity_id"]
        l59.add_individual(state, {
            "id": ident,
            "species_id": "native_actor",
            "age_steps": 0,
            "alive": bool(entity.get("alive", True)),
            "traits": _traits_from_actor(entity),
            "resources": {"food": 0.0, "water": 0.0},
            "knowledge": [],
            "lexicon": [],
            "relationship_ids": [],
        })
    l59.validate_state(state)
    return state


def _native_masses(projection: Mapping[str, Any]) -> dict[str, float]:
    totals = {"food": 0.0, "water": 0.0, "tree": 0.0, "animal": 0.0, "forage": 0.0}
    for entity in projection["snapshot"]["entities"]:
        kind = entity.get("kind")
        if kind == "resource":
            if entity.get("entity_id") == "resource-1":
                totals["food"] += max(0.0, float(entity.get("mass_kg", 0.0)))
            elif entity.get("entity_id") == "resource-2":
                totals["water"] += max(0.0, float(entity.get("mass_kg", 0.0)))
        elif kind in totals:
            totals[kind] += max(0.0, float(entity.get("mass_kg", 0.0)))
    return totals


def _initial_m03(manifest: Mapping[str, Any], projection: Mapping[str, Any]) -> dict[str, Any]:
    cell = manifest["cells"][0]
    native = _native_masses(projection)
    climate = projection["climate"]
    organic = max(0.1, native["tree"] * 0.02 + sum(float(h.get("organic_matter_kg", 0.0)) for h in cell["horizons"]))
    soil_nutrients = {
        nutrient: max(0.01, sum(float(h.get("nutrients_available", {}).get(nutrient, 0.0)) for h in cell["horizons"]))
        for nutrient in ("N", "P", "K")
    }
    habitats: dict[str, dict[str, Any]] = {
        "soil-native": {
            "kind": "soil",
            "substrates": {"plant_litter": organic, "root_exudate": max(0.05, organic * 0.08)},
            "available_nutrients": soil_nutrients,
            "temperature_c": climate["ambient_c"],
            "moisture": float(cell.get("moisture", 0.5)),
            "oxygen": 0.8,
        },
        "litter-native": {
            "kind": "litter",
            "substrates": {"deadwood": max(0.1, native["tree"] * 0.02), "plant_litter": max(0.1, native["forage"] * 0.1)},
            "temperature_c": climate["ambient_c"],
            "moisture": float(cell.get("moisture", 0.5)),
            "oxygen": 0.75,
        },
        "water-native": {
            "kind": "water",
            "substrates": {"dissolved_organic": max(0.05, native["water"] * 0.001)},
            "temperature_c": climate["ambient_c"],
            "moisture": 1.0,
            "oxygen": 0.7,
        },
        "food-native": {
            "kind": "food",
            "substrates": {"food": max(0.05, native["food"] * 0.01)},
            "temperature_c": climate["ambient_c"],
            "moisture": 0.7,
            "oxygen": 0.55,
        },
        "container-native": {
            "kind": "container",
            "substrates": {},
            "temperature_c": climate["ambient_c"],
            "moisture": 0.5,
            "oxygen": 0.5,
        },
    }
    for actor in _entities(projection, "actor"):
        habitats[f"host-{actor['entity_id']}"] = {
            "kind": "host",
            "substrates": {"host_waste": 0.0},
            "temperature_c": climate["ambient_c"],
            "moisture": 0.55,
            "oxygen": 0.65,
        }
    inocula = [
        {"habitat_id": "soil-native", "guild": "aerobic_decomposer", "biomass_kg": 0.05, "source": "native-world-observation"},
        {"habitat_id": "food-native", "guild": "yeast_fermenter", "biomass_kg": 0.01, "source": "native-world-observation"},
    ]
    return m03.initial(seed=_native_seed(projection), habitats=habitats, inocula=inocula)


def _initial_state(projection: Mapping[str, Any], run_id: str,
                   biological_step_s: float) -> dict[str, Any]:
    manifest = g01.generate(_native_seed(projection), _world_config(projection))
    plants = g47.initialize(manifest, initial_plants=0)
    # The temporary source is kept only while adding the native tree records;
    # it is removed by _add_native_trees before validation.
    plants["source_cells_manifest"] = manifest
    tree_map = _add_native_trees(plants, projection)
    microbial = _initial_m03(manifest, projection)
    routes = [
        {"route_id": "native-soil-litter", "source_habitat": "soil-native", "target_habitat": "litter-native", "kind": "native-adjacency", "capacity_kg": 2.0},
        {"route_id": "native-food-container", "source_habitat": "food-native", "target_habitat": "container-native", "kind": "native-container", "capacity_kg": 1.0},
    ]
    overlay = m48.adapt_m03(microbial, routes=routes, seed=_native_seed(projection))
    state = {
        "schema": SCHEMA,
        "version": VERSION,
        "g01": manifest,
        "g47": plants,
        "l02": _initial_l02(projection, run_id),
        "l59": _initial_l59(projection, run_id),
        "m03": microbial,
        "m48": overlay,
        "adapter": {
            "actor_ids": _actor_ids(projection),
            "tree_map": tree_map,
            "native_resource_ids": {
                "food": "resource-1", "water": "resource-2",
            },
            "native_observations": deepcopy(projection),
            "native_bindings": {
                "g01": "native seed, bounds and climate drive the copied terrain sidecar",
                "g47": "native tree observations are mapped to copied plant records; native trees remain authoritative",
                "l02": "native actor identities, elapsed time and completed public receipts",
                "l59": "native actor identities, elapsed time and alive status",
                "m03": "native climate and bounded resource observations initialize and drive habitats",
                "m48": "native climate drives the copied strain/fermentation overlay; M03 remains its source boundary",
            },
            "biological_step_s": float(biological_step_s),
            "clock_accumulator_s": 0.0,
            "last_native_tick": int(projection["snapshot"]["tick"]),
            "last_native_state_hash": None,
            "m03_initial_state_hash": m03.state_hash(microbial),
            "mapping_notes": [
                "Native UW10W trees do not expose G47 taxonomy; tree observations use declared G47 adapter species.",
                "Native actors do not expose reproductive roles; L02/L59 register non-reproductive resident records.",
                "Native resource masses are copied into bounded ecology habitats at attach and retained as observations thereafter.",
                "M7 disease remains disabled.",
            ],
        },
    }
    state["adapter"]["last_native_state_hash"] = _projection_hash(projection)
    _validate_state(state)
    return state


def _read_meta(db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("SELECT payload,checksum FROM living_bridge_meta WHERE singleton=1").fetchone()
    if row is None or _hash_text(row[0]) != row[1]:
        raise ValueError("living bridge metadata checksum mismatch")
    meta = _loads(row[0])
    if meta.get("schema") != SCHEMA or meta.get("rule") != RULE or meta.get("version") != VERSION:
        raise ValueError("unsupported living bridge schema")
    return meta


def _read_state(db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("SELECT payload,checksum FROM living_bridge_state WHERE singleton=1").fetchone()
    if row is None or _hash_text(row[0]) != row[1]:
        raise ValueError("living bridge state checksum mismatch")
    state = _loads(row[0])
    _validate_state(state)
    return state


def _write_meta(db: sqlite3.Connection, meta: Mapping[str, Any]) -> None:
    text = _dumps(meta)
    db.execute("UPDATE living_bridge_meta SET payload=?,checksum=? WHERE singleton=1",
               (text, _hash_text(text)))


def _write_state(db: sqlite3.Connection, state: Mapping[str, Any]) -> None:
    _validate_state(state)
    text = _dumps(state)
    db.execute("UPDATE living_bridge_state SET payload=?,checksum=? WHERE singleton=1",
               (text, _hash_text(text)))


def _validate_state(state: Mapping[str, Any]) -> None:
    expected = {"schema", "version", "g01", "g47", "l02", "l59", "m03", "m48", "adapter"}
    if not isinstance(state, Mapping) or set(state) != expected or state["schema"] != SCHEMA or state["version"] != VERSION:
        raise ValueError("unsupported living bridge state")
    g01.validate_manifest(state["g01"])
    g47.validate_state(state["g47"])
    l02.validate_state(state["l02"])
    l59.validate_state(state["l59"])
    m03.validate(state["m03"])
    m48.validate(state["m48"])
    adapter = state["adapter"]
    if type(adapter.get("actor_ids")) is not list or adapter["actor_ids"] != sorted(adapter["actor_ids"]):
        raise ValueError("living bridge actor manifest is not canonical")
    if type(adapter.get("tree_map")) is not dict:
        raise ValueError("living bridge tree map is invalid")
    _finite(adapter.get("biological_step_s"), "biological_step_s", 0.001, 31 * 86400.0)
    _finite(adapter.get("clock_accumulator_s"), "clock_accumulator_s", 0.0)
    if type(adapter.get("last_native_tick")) is not int or adapter["last_native_tick"] < 0:
        raise ValueError("living bridge native tick is invalid")
    if adapter.get("m03_initial_state_hash") != state["m48"].get("m03_source_hash"):
        raise ValueError("M48 source boundary does not match the attached M03 state")
    if set(state["l02"]["individuals"]) != set(adapter["actor_ids"]):
        raise ValueError("L02 actor binding is incomplete")
    if set(state["l59"]["individuals"]) != set(adapter["actor_ids"]):
        raise ValueError("L59 actor binding is incomplete")


def _native_effect(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, Mapping):
        return None
    native = result.get("native") if isinstance(result.get("native"), Mapping) else result
    if not isinstance(native, Mapping):
        return None
    request = native.get("request")
    receipt = native.get("receipt")
    if not isinstance(request, Mapping) or not isinstance(receipt, Mapping):
        return None
    return {
        "agent_id": request.get("agent_id"),
        "action_type": request.get("action_type"),
        "target_ids": list(request.get("target_ids", [])),
        "request_id": request.get("request_id"),
        "status": receipt.get("status"),
        "tick": int(native.get("after", {}).get("tick", 0)) if isinstance(native.get("after"), Mapping) else None,
    }


def _update_g47_conditions(state: dict[str, Any]) -> None:
    source_cells = state["g47"].get("source_cells", {})
    for cell in state["g01"]["cells"]:
        key = f"{cell['coord']['x']},{cell['coord']['y']}"
        if key not in source_cells:
            continue
        current = source_cells[key]
        for field in ("moisture", "surface_water_m3", "standing_water", "plant_condition"):
            current[field] = deepcopy(cell[field])
    state["g47"]["state_hash"] = g47.state_hash(state["g47"])


def _sync_native_trees(state: dict[str, Any], projection: Mapping[str, Any]) -> None:
    mapping = state["adapter"]["tree_map"]
    entities = {entity["entity_id"]: entity for entity in _entities(projection, "tree")}
    for native_id, plant_id in mapping.items():
        plant = next((item for item in state["g47"]["plants"] if item["plant_id"] == plant_id), None)
        if plant is None:
            continue
        entity = entities.get(native_id)
        if entity is None or not bool(entity.get("alive", True)):
            plant["alive"] = False
            plant["biomass_kg"] = 0.0
            plant["stage"] = "dead"
            continue
        traits = state["g47"]["species_catalog"][plant["species_id"]]
        plant["alive"] = True
        plant["stage"] = "adult" if entity.get("stage") in {"mature", "old"} else "juvenile"
        plant["biomass_kg"] = round(max(0.01, min(float(traits["max_biomass_kg"]), float(entity.get("mass_kg", 0.01)))), 8)
        plant["reserve_kg"] = round(plant["biomass_kg"] * float(traits["root_reserve_fraction"]), 8)
    state["g47"]["state_hash"] = g47.state_hash(state["g47"])


def _set_ecology_environment(state: dict[str, Any], projection: Mapping[str, Any]) -> None:
    climate = projection["climate"]
    cell = state["g01"]["cells"][0]
    moisture = max(0.0, min(1.0, float(cell.get("moisture", 0.5))))
    for habitat in state["m03"]["habitats"].values():
        kind = habitat["kind"]
        habitat["environment"]["temperature_c"] = float(climate["ambient_c"])
        habitat["environment"]["moisture"] = 1.0 if kind == "water" else moisture if kind in {"soil", "litter"} else 0.7 if kind == "food" else 0.5
        habitat["environment"]["oxygen"] = 0.7 if kind == "water" else 0.8 if kind == "soil" else 0.75 if kind == "litter" else 0.55 if kind == "food" else 0.5
    for habitat in state["m48"]["habitats"].values():
        kind = habitat["kind"]
        habitat["environment"]["temperature_c"] = float(climate["ambient_c"])
        habitat["environment"]["moisture"] = 1.0 if kind == "water" else moisture if kind in {"soil", "litter"} else 0.7 if kind == "food" else 0.5
        habitat["environment"]["oxygen"] = 0.7 if kind == "water" else 0.8 if kind == "soil" else 0.75 if kind == "litter" else 0.55 if kind == "food" else 0.5


def _sync_actor_status(state: dict[str, Any], projection: Mapping[str, Any]) -> None:
    actors = {entity["entity_id"]: entity for entity in _entities(projection, "actor")}
    for ident, entity in actors.items():
        alive = bool(entity.get("alive", True))
        if ident in state["l02"]["individuals"]:
            state["l02"]["individuals"][ident]["alive"] = alive
        if ident in state["l59"]["individuals"]:
            state["l59"]["individuals"][ident]["alive"] = alive


def _record_native_relationships(state: dict[str, Any], effect: Mapping[str, Any] | None,
                                 operation_id: str) -> None:
    if not effect or effect.get("status") != "completed":
        return
    actor = effect.get("agent_id")
    if actor not in state["l02"]["individuals"]:
        return
    action = effect.get("action_type")
    if action not in {"give", "speak"}:
        return
    kind = "reliable_help" if action == "give" else "shared_activity"
    for target in effect.get("target_ids", []):
        if target not in state["l02"]["individuals"] or target == actor:
            continue
        evidence = l02.relationship_evidence(
            actor, target, f"native:{operation_id}:{actor}:{target}",
            kind, int(effect.get("tick") or 0), 1.0, 0.0, "native_receipt",
        )
        l02.record_relationship(state["l02"], evidence)


def _advance_sidecars(state: Mapping[str, Any], before: Mapping[str, Any],
                      after: Mapping[str, Any], effect: Mapping[str, Any] | None,
                      operation_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(dict(state))
    before_snapshot = before["snapshot"]
    after_snapshot = after["snapshot"]
    before_tick = int(before_snapshot["tick"])
    after_tick = int(after_snapshot["tick"])
    if after_tick < before_tick:
        raise ValueError("native tick moved backward during living bridge operation")
    elapsed_s = max(0.0, float(after_snapshot["simulated_time_s"]) - float(before_snapshot["simulated_time_s"]))
    if elapsed_s > 0.0:
        climate = after["climate"]
        rainfall = max(0.0, float(climate.get("rain_mm_h", 0.0))) * elapsed_s / 3600.0
        result["g01"] = g01.soil_step(
            result["g01"], rainfall_mm=rainfall,
            temperature_c=float(climate.get("ambient_c", 15.0)),
            daylight_fraction=float(climate.get("daylight_factor", 0.5)),
            dt_days=elapsed_s / 86400.0,
        )
        _update_g47_conditions(result)
        result["g47"] = g47.plant_step(
            result["g47"], days=elapsed_s / 86400.0,
            rainfall_mm=rainfall,
            temperature_c=float(climate.get("ambient_c", 15.0)),
            daylight_fraction=float(climate.get("daylight_factor", 0.5)),
            operation_id=f"{operation_id}-g47",
        )
        _sync_native_trees(result, after)
        _set_ecology_environment(result, after)
        result["m03"] = m03.step(result["m03"], elapsed_s)
        result["m48"] = m48.step(result["m48"], elapsed_s)
    adapter = result["adapter"]
    adapter["clock_accumulator_s"] = float(adapter["clock_accumulator_s"]) + elapsed_s
    biological_step_s = float(adapter["biological_step_s"])
    biological_steps = int(adapter["clock_accumulator_s"] // biological_step_s)
    if biological_steps:
        l02.advance_time(result["l02"], biological_steps)
        l59.advance_time(result["l59"], biological_steps)
        adapter["clock_accumulator_s"] = round(adapter["clock_accumulator_s"] - biological_steps * biological_step_s, 9)
    _sync_actor_status(result, after)
    _record_native_relationships(result, effect, operation_id)
    adapter["native_observations"] = deepcopy(after)
    adapter["last_native_tick"] = after_tick
    adapter["last_native_state_hash"] = after.get("native_state_hash", adapter.get("last_native_state_hash"))
    _validate_state(result)
    return result, {
        "native_tick_before": before_tick,
        "native_tick_after": after_tick,
        "native_elapsed_s": elapsed_s,
        "biological_steps": biological_steps,
        "sidecar_revisions": {
            "g01": result["g01"]["revision"],
            "g47": result["g47"]["revision"],
            "l02": result["l02"]["clock_step"],
            "l59": result["l59"]["clock_step"],
            "m03": result["m03"]["revision"],
            "m48": result["m48"]["revision"],
        },
    }


def _stored_operation(db: sqlite3.Connection, operation_id: str,
                      command: Mapping[str, Any]) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT command,before_hash,after_hash,native_before_hash,native_after_hash,result "
        "FROM living_bridge_operations WHERE operation_id=?", (operation_id,)
    ).fetchone()
    if row is None:
        return None
    if _loads(row[0]) != command:
        raise ValueError("conflicting living bridge operation identity")
    result = _loads(row[5])
    result.update({
        "operation_id": operation_id,
        "before_hash": row[1],
        "after_hash": row[2],
        "native_before_hash": row[3],
        "native_after_hash": row[4],
        "idempotent": True,
    })
    return result


def _operation_id(command: Mapping[str, Any], operation_id: str | None) -> str:
    if operation_id is None:
        return "living-" + _hash_text(_dumps(command))[:32]
    if not isinstance(operation_id, str) or not _ID_RE.fullmatch(operation_id):
        raise ValueError("invalid living bridge operation ID")
    return operation_id


def _life_native_commit(db: sqlite3.Connection, world: Any, policies: dict[str, Any],
                        people: dict[str, Any], command: Mapping[str, Any],
                        logical_id: str) -> tuple[Any, str, str]:
    prior = db.execute("SELECT command,result FROM life_operations WHERE logical_id=?", (logical_id,)).fetchone()
    if prior is not None:
        raise ValueError("native life operation exists without a living bridge operation")
    before = life_store.token(world, policies, people)

    def emit(native_command: Mapping[str, Any]) -> Any:
        if db.execute("SELECT COUNT(*) FROM weather_operations").fetchone()[0] >= 25000:
            raise ValueError("physical journal quota reached")
        old = weather.digest(world.checkpoint())
        native_result = weather.apply(world, native_command, policies)
        db.execute(
            "INSERT INTO weather_operations(command,before_hash,after_hash,result) VALUES(?,?,?,?)",
            (_dumps(native_command), old, weather.digest(world.checkpoint()), _dumps(native_result)),
        )
        return native_result

    result = life_store._backend.apply(world, policies, people, command, logical_id, emit)
    world.check_invariants()
    after = life_store.token(world, policies, people)
    return result, before, after


def attach(source: str | Path, destination: str | Path, *,
           biological_step_s: float = 86400.0, mode: str = "connected") -> dict[str, Any]:
    """Enroll an existing life-compatible world into a new bridge copy."""
    biological_step_s = _finite(biological_step_s, "biological_step_s", 0.001, 31 * 86400.0)
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    source_hash = _file_hash(source)
    if _has_tables(source, {"life_meta", "life_head", "life_operations"}):
        _copy_database(source, destination)
    else:
        life_store.attach(source, destination, mode=mode)
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed during living bridge attach")
    with Lease(destination), closing(weather.connect(destination, False)) as db:
        db.execute("BEGIN IMMEDIATE")
        world, _, _, native_life_meta = life_store.head(db)
        projection = _native_projection(world)
        native_hash = weather.digest(world.checkpoint())
        run_id = projection["snapshot"].get("run_id") or native_life_meta.get("run_id") or "living-run"
        state = _initial_state(projection, run_id, biological_step_s)
        state["adapter"]["last_native_state_hash"] = native_hash
        _validate_state(state)
        meta = {
            "schema": SCHEMA,
            "rule": RULE,
            "version": VERSION,
            "run_id": run_id,
            "actors": list(state["adapter"]["actor_ids"]),
            "source_db_sha256": source_hash,
            "source_native_state_hash": native_hash,
            "source_life_meta": deepcopy(native_life_meta),
            "native_schema": {"weather_format": "ALICE-WEATHER-2", "bridge": SCHEMA},
            "state_hash": _state_hash(state),
            "last_operation_id": "living-attach-" + source_hash[:24],
            "last_native_state_hash": native_hash,
            "initial_state": deepcopy(state),
            "initial_native_projection": deepcopy(projection),
            "operation_quota": MAX_OPERATIONS,
        }
        db.executescript("""
            CREATE TABLE living_bridge_meta(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                payload TEXT NOT NULL,
                checksum TEXT NOT NULL
            );
            CREATE TABLE living_bridge_state(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                payload TEXT NOT NULL,
                checksum TEXT NOT NULL
            );
            CREATE TABLE living_bridge_operations(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL UNIQUE,
                command TEXT NOT NULL,
                before_hash TEXT NOT NULL,
                after_hash TEXT NOT NULL,
                native_before_hash TEXT NOT NULL,
                native_after_hash TEXT NOT NULL,
                native_before TEXT NOT NULL,
                native_after TEXT NOT NULL,
                native_effect TEXT NOT NULL,
                result TEXT NOT NULL
            );
            CREATE INDEX living_bridge_operation_identity ON living_bridge_operations(operation_id);
        """)
        meta_text = _dumps(meta)
        state_text = _dumps(state)
        db.execute("INSERT INTO living_bridge_meta VALUES(1,?,?)", (meta_text, _hash_text(meta_text)))
        db.execute("INSERT INTO living_bridge_state VALUES(1,?,?)", (state_text, _hash_text(state_text)))
        attach_command = {"kind": "attach", "source_db_sha256": source_hash, "actors": state["adapter"]["actor_ids"]}
        attach_result = {"changed": False, "native_tick": int(projection["snapshot"]["tick"]), "sidecars_initialized": ["g01", "g47", "l02", "l59", "m03", "m48"]}
        db.execute(
            "INSERT INTO living_bridge_operations(operation_id,command,before_hash,after_hash,native_before_hash,native_after_hash,native_before,native_after,native_effect,result) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (meta["last_operation_id"], _dumps(attach_command), EMPTY_HASH, meta["state_hash"],
             native_hash, native_hash, _dumps(projection), _dumps(projection), "{}", _dumps(attach_result)),
        )
        db.commit()
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed after living bridge attach")
    return inspect(destination)


def commit(path: str | Path, command: Mapping[str, Any], operation_id: str | None = None) -> dict[str, Any]:
    """Apply one native life command and its matching sidecar advancement atomically."""
    if not isinstance(command, Mapping) or not isinstance(command.get("kind"), str):
        raise ValueError("living bridge command must contain a kind")
    command = deepcopy(dict(command))
    op_id = _operation_id(command, operation_id)
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute("BEGIN IMMEDIATE")
        meta = _read_meta(db)
        state = _read_state(db)
        stored = _stored_operation(db, op_id, command)
        if stored is not None:
            db.commit()
            return stored
        world, policies, people, _ = life_store.head(db)
        before_projection = _native_projection(world)
        before_native_hash = weather.digest(world.checkpoint())
        if before_native_hash != meta["last_native_state_hash"]:
            raise ValueError("native world changed outside the living bridge")
        result, life_before, life_after = _life_native_commit(db, world, policies, people, command, op_id)
        after_projection = _native_projection(world)
        after_native_hash = weather.digest(world.checkpoint())
        after_projection["native_state_hash"] = after_native_hash
        before_projection["native_state_hash"] = before_native_hash
        effect = _native_effect(result)
        next_state, sidecar_result = _advance_sidecars(state, before_projection, after_projection, effect, op_id)
        after_state_hash = _state_hash(next_state)
        result_payload = {
            "native_effect": effect,
            "native_result": deepcopy(result),
            "sidecars": sidecar_result,
        }
        if db.execute("SELECT COUNT(*) FROM living_bridge_operations").fetchone()[0] >= MAX_OPERATIONS:
            raise ValueError("living bridge operation quota reached")
        db.execute(
            "UPDATE weather_head SET state=?,hash=?,policy=?,policy_hash=? WHERE id=1",
            (world.checkpoint(), after_native_hash, _dumps(policies), weather.digest(_dumps(policies))),
        )
        db.execute(
            "UPDATE life_head SET people=?,hash=? WHERE id=1",
            (_dumps(people), life_after),
        )
        db.execute(
            "INSERT INTO life_operations(logical_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
            (op_id, _dumps(command), life_before, life_after, _dumps(result)),
        )
        meta["state_hash"] = after_state_hash
        meta["last_operation_id"] = op_id
        meta["last_native_state_hash"] = after_native_hash
        _write_state(db, next_state)
        _write_meta(db, meta)
        db.execute(
            "INSERT INTO living_bridge_operations(operation_id,command,before_hash,after_hash,native_before_hash,native_after_hash,native_before,native_after,native_effect,result) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (op_id, _dumps(command), _state_hash(state), after_state_hash,
             before_native_hash, after_native_hash, _dumps(before_projection),
             _dumps(after_projection), _dumps(effect or {}), _dumps(result_payload)),
        )
        db.commit()
    return dict(result_payload, operation_id=op_id, before_hash=_state_hash(state),
                after_hash=after_state_hash, native_before_hash=before_native_hash,
                native_after_hash=after_native_hash, idempotent=False)


def run(path: str | Path, ticks: int, *, logical_prefix: str = "living-run") -> dict[str, Any]:
    """Advance the connected world by an explicit number of native ticks."""
    if type(ticks) is not int or ticks < 0 or ticks > 10000:
        raise ValueError("ticks must be an integer in [0, 10000]")
    for index in range(ticks):
        commit(path, {"kind": "step", "ticks": 1}, f"{logical_prefix}-{index}")
    return inspect(path)


def _sidecar_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "g01": g01.inspect(state["g01"]),
        "g47": g47.inspect(state["g47"]),
        "l02": {
            "clock_step": state["l02"]["clock_step"],
            "individual_count": len(state["l02"]["individuals"]),
            "relationship_count": len(state["l02"]["relationships"]),
            "pregnancy_count": len(state["l02"]["pregnancies"]),
        },
        "l59": l59.demographic_report(state["l59"]) | {"clock_step": state["l59"]["clock_step"]},
        "m03": m03.inspect(state["m03"]),
        "m48": m48.inspect(state["m48"]),
    }


def inspect(path: str | Path) -> dict[str, Any]:
    with closing(weather.connect(path)) as db:
        db.execute("BEGIN")
        meta = _read_meta(db)
        state = _read_state(db)
        world, _, _, _ = life_store.head(db)
        projection = _native_projection(world)
        native_hash = weather.digest(world.checkpoint())
        return {
            "schema": SCHEMA,
            "rule": RULE,
            "version": VERSION,
            "run_id": meta["run_id"],
            "actors": list(meta["actors"]),
            "native_tick": int(projection["snapshot"]["tick"]),
            "native_simulated_time_s": float(projection["snapshot"]["simulated_time_s"]),
            "native_state_hash": native_hash,
            "source_db_sha256": meta["source_db_sha256"],
            "source_native_state_hash": meta["source_native_state_hash"],
            "state_hash": meta["state_hash"],
            "operation_count": db.execute("SELECT COUNT(*) FROM living_bridge_operations").fetchone()[0],
            "native": projection,
            "sidecars": _sidecar_summary(state),
            "bindings": deepcopy(state["adapter"]["native_bindings"]),
            "mapping_notes": list(state["adapter"]["mapping_notes"]),
        }


def state(path: str | Path) -> dict[str, Any]:
    """Return a validated deep copy for tests and local inspection tools."""
    with closing(weather.connect(path)) as db:
        db.execute("BEGIN")
        return _read_state(db)


def save(path: str | Path, destination: str | Path) -> dict[str, Any]:
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("living bridge backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Lease(path), closing(weather.connect(path)) as source:
        with destination.open("xb"):
            pass
        try:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("living bridge backup integrity check failed")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return inspect(destination)


def replay(path: str | Path) -> dict[str, Any]:
    """Verify native/life journals and deterministically replay the sidecar chain."""
    with closing(weather.connect(path)) as db:
        db.execute("BEGIN")
        meta = _read_meta(db)
        stored = _read_state(db)
        current_native_hash = weather.digest(life_store.head(db)[0].checkpoint())
        if current_native_hash != meta["last_native_state_hash"]:
            raise ValueError("living bridge native head differs from metadata")
        replayed = deepcopy(meta["initial_state"])
        _validate_state(replayed)
        count = 0
        for row in db.execute(
            "SELECT operation_id,command,before_hash,after_hash,native_before_hash,native_after_hash,native_before,native_after,native_effect,result "
            "FROM living_bridge_operations ORDER BY seq"
        ):
            op_id, command_text, before_hash, after_hash, native_before_hash, native_after_hash, before_text, after_text, effect_text, result_text = row
            command = _loads(command_text)
            if command.get("kind") == "attach":
                if before_hash != EMPTY_HASH or after_hash != _state_hash(replayed):
                    raise ValueError("living bridge attach chain mismatch")
                count += 1
                continue
            if before_hash != _state_hash(replayed):
                raise ValueError("living bridge operation chain mismatch")
            before = _loads(before_text)
            after = _loads(after_text)
            effect = _loads(effect_text)
            replayed, sidecar_result = _advance_sidecars(replayed, before, after, effect or None, op_id)
            expected_result = {
                "native_effect": effect or None,
                "native_result": _loads(result_text)["native_result"],
                "sidecars": sidecar_result,
            }
            expected_after = _state_hash(replayed)
            if after_hash != expected_after or _dumps(expected_result) != result_text:
                raise ValueError("living bridge operation result or state mismatch")
            count += 1
        if _state_hash(stored) != _state_hash(replayed) or meta["state_hash"] != _state_hash(replayed):
            raise ValueError("living bridge final replay mismatch")
    native_replay = weather.replay(path)
    life_replay = life_store.replay(path)
    return {
        "replay_matches": True,
        "operations": count,
        "state_hash": _state_hash(replayed),
        "native": native_replay,
        "life": life_replay,
    }


def resume(path: str | Path) -> dict[str, Any]:
    result = inspect(path)
    result["replay"] = replay(path)
    return result


__all__ = [
    "RULE", "SCHEMA", "VERSION", "attach", "commit", "run", "inspect", "state",
    "save", "replay", "resume",
]
