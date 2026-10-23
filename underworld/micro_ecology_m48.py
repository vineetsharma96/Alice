"""Bounded additive M4-M8 microbial ecology overlay.

The overlay consumes a validated M0-M3 state through :func:`adapt_m03` and
never writes back to that state.  It owns only its copied experimental stocks,
finite dispersal graph, strain traits and fictional fermentation vessels.  The
implementation is deliberately standard-library only and JSON friendly.

M4 provides explicit finite dispersal, competition and bounded heritable
traits.  M5 provides a fictional food/container fermentation ledger with
oxygen, temperature, seal and vent constraints.  M6 is an optional observer
microcosm conversion which is representation-only.  M7 remains disabled; no
pathogen state or implementation is present.  M8 is limited to checkpoint,
replay and adapter boundaries rather than live-world integration.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import micro_ecology_m03 as m03


RULE = "alice.micro-ecology.m48/v1"
VERSION = "m48.1"
EPSILON = 1e-10
MAX_STEP_S = 31 * 86400.0
MAX_ROUTES = 512
MAX_STRAINS_PER_HABITAT = 128
MAX_FERMENTATIONS = 128
MAX_EVENTS = 256
MAX_MICROCOSM_CELLS = 256
NUTRIENTS = m03.NUTRIENTS
GUILDS = m03.GUILDS
FORBIDDEN_FIELD_TOKENS = m03.FORBIDDEN_FIELD_TOKENS


class EcologyConflictError(ValueError):
    """Raised when a caller supplies a stale M48 revision."""


def _reject_forbidden(value: Any, label: str = "value") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{label} fields must be strings")
            if any(token in key.lower() for token in FORBIDDEN_FIELD_TOKENS):
                raise ValueError("private/operator/model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden(item, label)


def _number(value: Any, label: str, low: float = 0.0, high: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if result < low or (high is not None and result > high):
        raise ValueError(f"{label} must be in [{low}, {high}]")
    return result


def _text(value: Any, label: str, maximum: int = 160) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{label} must be a non-empty short string")
    return value


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def state_hash(state: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(state))
    body.pop("state_hash", None)
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _nutrients(values: Mapping[str, Any] | None = None) -> dict[str, float]:
    values = values or {}
    return {key: _number(values.get(key, 0.0), f"nutrient {key}") for key in NUTRIENTS}


def _traits(values: Mapping[str, Any] | None = None) -> dict[str, Any]:
    values = values or {}
    return {
        "uptake_affinity": _number(values.get("uptake_affinity", 1.0), "uptake_affinity", 0.5, 1.5),
        "maintenance_multiplier": _number(values.get("maintenance_multiplier", 1.0), "maintenance_multiplier", 0.5, 1.5),
        "temperature_tolerance": _number(values.get("temperature_tolerance", 1.0), "temperature_tolerance", 0.5, 1.5),
        "mutation_rate": _number(values.get("mutation_rate", 0.0), "mutation_rate", 0.0, 0.25),
        "mutation_enabled": bool(values.get("mutation_enabled", False)),
    }


def _copy_substrates(habitat: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for name, record in habitat.get("substrates", {}).items():
        result[str(name)] = {
            "mass_kg": _number(record.get("mass_kg", 0.0), f"substrate {name} mass"),
            "nutrients": _nutrients(record.get("nutrients")),
            "accessibility": _number(record.get("accessibility", 0.8), "accessibility", 0.0, 1.0),
        }
    return result


def _default_population_traits(population: Mapping[str, Any]) -> dict[str, Any]:
    return _traits({"mutation_enabled": False, "mutation_rate": 0.0})


def _strain_id(guild: str, lineage_id: str) -> str:
    return f"{guild}::{lineage_id}"


def _new_population(guild: str, biomass: float, lineage_id: str, source: str, traits: Mapping[str, Any] | None = None, ancestor_id: str | None = None, generation: int = 0) -> dict[str, Any]:
    return {
        "strain_id": _strain_id(guild, lineage_id),
        "guild": guild,
        "lineage_id": lineage_id,
        "ancestor_id": ancestor_id,
        "generation": int(generation),
        "biomass_kg": _number(biomass, "strain biomass"),
        "reserves_kg": 0.0,
        "nutrients": _nutrients(),
        "traits": _traits(traits),
        "inoculum_sources": [_text(source, "inoculum source")],
        "activity": "active" if biomass > EPSILON else "dormant",
        "division_progress": 0.0,
        "division_events": 0,
        "mutation_events": 0,
        "ancestor_control": copy.deepcopy(_traits(traits)),
    }


def _copy_habitat(habitat_id: str, habitat: Mapping[str, Any]) -> dict[str, Any]:
    environment = copy.deepcopy(habitat.get("environment", {}))
    environment.setdefault("temperature_c", 20.0)
    environment.setdefault("moisture", 0.6)
    environment.setdefault("oxygen", 0.7)
    populations: dict[str, dict[str, Any]] = {}
    for guild, source_population in habitat.get("populations", {}).items():
        if guild not in GUILDS:
            continue
        lineage = str(source_population.get("lineage_id", f"m03-{guild}"))
        population = _new_population(
            guild,
            source_population.get("biomass_kg", 0.0),
            lineage,
            (source_population.get("inoculum_sources") or ["m03-adapter"])[-1],
            _default_population_traits(source_population),
        )
        population["reserves_kg"] = _number(source_population.get("reserves_kg", 0.0), "strain reserves")
        population["nutrients"] = _nutrients(source_population.get("nutrients"))
        population["activity"] = source_population.get("activity", population["activity"])
        populations[population["strain_id"]] = population
    return {
        "habitat_id": habitat_id,
        "kind": habitat.get("kind", "soil"),
        "environment": {
            "temperature_c": _number(environment["temperature_c"], "temperature_c", -80.0, 100.0),
            "moisture": _number(environment["moisture"], "moisture", 0.0, 1.0),
            "oxygen": _number(environment["oxygen"], "oxygen", 0.0, 1.0),
        },
        "substrates": _copy_substrates(habitat),
        "available_nutrients": _nutrients(habitat.get("available_nutrients")),
        "dead_biomass_kg": _number(habitat.get("dead_biomass_kg", 0.0), "dead biomass"),
        "dead_nutrients": _nutrients(habitat.get("dead_nutrients")),
        "byproducts": {str(k): _number(v, f"byproduct {k}") for k, v in habitat.get("byproducts", {}).items()},
        "populations": populations,
        "events": [],
    }


def _normal_route(route: Mapping[str, Any], index: int, habitats: Mapping[str, Any]) -> dict[str, Any]:
    source = _text(route.get("source_habitat", route.get("source")), "route source")
    target = _text(route.get("target_habitat", route.get("target")), "route target")
    if source == target or source not in habitats or target not in habitats:
        raise ValueError("route endpoints must be distinct known habitats")
    route_id = _text(route.get("route_id", f"{source}->{target}:{index}"), "route_id")
    return {
        "route_id": route_id,
        "source_habitat": source,
        "target_habitat": target,
        "kind": _text(route.get("kind", "declared"), "route kind"),
        "capacity_kg": _number(route.get("capacity_kg", 1.0), "route capacity", 0.0),
        "used_kg": _number(route.get("used_kg", 0.0), "route used", 0.0),
        "enabled": bool(route.get("enabled", True)),
        "sealed_blocked": bool(route.get("sealed_blocked", False)),
    }


def _total_organic(state: Mapping[str, Any]) -> float:
    total = 0.0
    for habitat in state["habitats"].values():
        total += sum(record["mass_kg"] for record in habitat["substrates"].values())
        total += habitat["dead_biomass_kg"]
        total += sum(pop["biomass_kg"] + pop["reserves_kg"] for pop in habitat["populations"].values())
        total += sum(habitat["byproducts"].values())
    for process in state["fermentations"].values():
        total += sum(process[key] for key in ("substrate_mass_kg", "culture_biomass_kg", "product_mass_kg", "byproduct_mass_kg", "gas_mass_kg"))
    return total


def _make_state(m03_state: Mapping[str, Any], routes: Sequence[Mapping[str, Any]] | None, seed: int | None) -> dict[str, Any]:
    source = m03.validate(m03_state)
    habitats = {hid: _copy_habitat(hid, habitat) for hid, habitat in source["habitats"].items()}
    normalized_routes = [_normal_route(item, index, habitats) for index, item in enumerate(routes or ())]
    if len(normalized_routes) > MAX_ROUTES:
        raise ValueError("route budget exceeded")
    result = {
        "rule": RULE,
        "version": VERSION,
        "seed": source["seed"] if seed is None else int(seed),
        "revision": 0,
        "time_s": 0.0,
        "m03_source_hash": m03.state_hash(source),
        "m03_source_revision": source["revision"],
        "habitats": habitats,
        "routes": normalized_routes,
        "transfer_events": [],
        "fermentations": {},
        "ledgers": {"organic_initial_kg": 0.0, "organic_boundary_kg": 0.0},
        "disease": {"status": "disabled", "manifest": None},
        "origin": "additive M4-M8 overlay; M03 remains source owner",
    }
    result["ledgers"]["organic_initial_kg"] = _total_organic(result)
    return result


def adapt_m03(m03_state: Mapping[str, Any], routes: Sequence[Mapping[str, Any]] | None = None, seed: int | None = None) -> dict[str, Any]:
    """Create an M48 overlay from a validated M03 snapshot without mutation."""
    _reject_forbidden(routes, "routes")
    result = _make_state(m03_state, routes, seed)
    validate(result)
    return result


initial_from_m03 = adapt_m03


def _copy_checked(state: Mapping[str, Any]) -> dict[str, Any]:
    validate(state)
    return copy.deepcopy(dict(state))


def validate(state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise ValueError("M48 state must be a mapping")
    _reject_forbidden(state, "state")
    expected = {"rule", "version", "seed", "revision", "time_s", "m03_source_hash", "m03_source_revision", "habitats", "routes", "transfer_events", "fermentations", "ledgers", "disease", "origin"}
    if set(state) != expected or state["rule"] != RULE or state["version"] != VERSION:
        raise ValueError("unsupported M48 ecology schema")
    if type(state["seed"]) is not int or type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("invalid M48 identity")
    _number(state["time_s"], "time_s")
    _text(state["m03_source_hash"], "m03_source_hash", 128)
    if type(state["m03_source_revision"]) is not int or state["m03_source_revision"] < 0:
        raise ValueError("invalid M03 source revision")
    if not isinstance(state["habitats"], Mapping) or not state["habitats"]:
        raise ValueError("invalid M48 habitats")
    for habitat_id, habitat in state["habitats"].items():
        if habitat.get("habitat_id") != habitat_id or habitat.get("kind") not in m03.HABITAT_KINDS:
            raise ValueError("invalid habitat identity")
        env = habitat["environment"]
        _number(env["temperature_c"], "temperature_c", -80.0, 100.0)
        _number(env["moisture"], "moisture", 0.0, 1.0)
        _number(env["oxygen"], "oxygen", 0.0, 1.0)
        for record in habitat["substrates"].values():
            _number(record["mass_kg"], "substrate mass")
            _number(record["accessibility"], "accessibility", 0.0, 1.0)
            if set(record["nutrients"]) != set(NUTRIENTS):
                raise ValueError("invalid substrate nutrients")
            for value in record["nutrients"].values():
                _number(value, "substrate nutrient")
        _number(habitat["dead_biomass_kg"], "dead biomass")
        for pool in (habitat["available_nutrients"], habitat["dead_nutrients"]):
            if set(pool) != set(NUTRIENTS):
                raise ValueError("invalid nutrient pool")
            for value in pool.values():
                _number(value, "nutrient")
        if len(habitat["populations"]) > MAX_STRAINS_PER_HABITAT:
            raise ValueError("strain budget exceeded")
        for strain_id, population in habitat["populations"].items():
            if population["strain_id"] != strain_id or population["guild"] not in GUILDS:
                raise ValueError("invalid strain")
            _text(population["lineage_id"], "lineage_id")
            if population["ancestor_id"] is not None:
                _text(population["ancestor_id"], "ancestor_id")
            if type(population["generation"]) is not int or population["generation"] < 0:
                raise ValueError("invalid strain generation")
            _number(population["biomass_kg"], "strain biomass")
            _number(population["reserves_kg"], "strain reserves")
            _traits(population["traits"])
            _traits(population["ancestor_control"])
            if population["activity"] not in ("active", "dormant"):
                raise ValueError("invalid strain activity")
            for key in ("division_events", "mutation_events"):
                if type(population[key]) is not int or population[key] < 0:
                    raise ValueError("invalid strain events")
            _number(population["division_progress"], "division progress", 0.0, 1.0)
            for value in population["nutrients"].values():
                _number(value, "strain nutrient")
    if not isinstance(state["routes"], list) or len(state["routes"]) > MAX_ROUTES:
        raise ValueError("route budget exceeded")
    route_ids = set()
    for route in state["routes"]:
        if route["route_id"] in route_ids:
            raise ValueError("route IDs must be unique")
        route_ids.add(route["route_id"])
        if route["source_habitat"] not in state["habitats"] or route["target_habitat"] not in state["habitats"]:
            raise ValueError("route endpoint missing")
        _number(route["capacity_kg"], "route capacity")
        _number(route["used_kg"], "route used")
        if route["used_kg"] > route["capacity_kg"] + EPSILON:
            raise ValueError("route capacity exceeded")
    if len(state["fermentations"]) > MAX_FERMENTATIONS:
        raise ValueError("fermentation budget exceeded")
    for process_id, process in state["fermentations"].items():
        if process["process_id"] != process_id or process["container_id"] not in state["habitats"]:
            raise ValueError("invalid fermentation process")
        for key in ("capacity_kg", "gas_capacity_kg", "substrate_mass_kg", "culture_biomass_kg", "product_mass_kg", "byproduct_mass_kg", "gas_mass_kg", "exported_mass_kg", "elapsed_s"):
            _number(process[key], f"fermentation {key}")
        if process["gas_mass_kg"] > process["gas_capacity_kg"] + EPSILON:
            raise ValueError("sealed gas capacity exceeded")
        if process["sealed"] and process["vented"] and process["gas_capacity_kg"] <= 0:
            raise ValueError("vented vessel needs gas capacity")
        _number(process["temperature_c"], "fermentation temperature", -80.0, 100.0)
        _number(process["oxygen"], "fermentation oxygen", 0.0, 1.0)
    if state["disease"] != {"status": "disabled", "manifest": None}:
        raise ValueError("M7 disease is deferred and disabled")
    _number(state["ledgers"]["organic_initial_kg"], "organic initial")
    _number(state["ledgers"]["organic_boundary_kg"], "organic boundary", -float("inf"), float("inf"))
    expected_total = state["ledgers"]["organic_initial_kg"] + state["ledgers"]["organic_boundary_kg"]
    if abs(_total_organic(state) - expected_total) > 2e-8:
        raise ValueError("M48 tracked organic conservation failed")
    return dict(state)


def add_route(state: Mapping[str, Any], route: Mapping[str, Any], expected_revision: int | None = None) -> dict[str, Any]:
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    result["routes"].append(_normal_route(route, len(result["routes"]), result["habitats"]))
    result["revision"] += 1
    validate(result)
    return result


def _find_population(habitat: Mapping[str, Any], strain_id: str | None = None, guild: str | None = None) -> tuple[str, dict[str, Any]]:
    if strain_id is not None:
        if strain_id not in habitat["populations"]:
            raise ValueError("unknown strain")
        return strain_id, habitat["populations"][strain_id]
    for key, population in habitat["populations"].items():
        if guild is None or population["guild"] == guild:
            return key, population
    raise ValueError("no matching source strain")


def inoculate_strain(state: Mapping[str, Any], habitat_id: str, guild: str, biomass_kg: float, source: str = "explicit_inoculum", traits: Mapping[str, Any] | None = None, expected_revision: int | None = None) -> dict[str, Any]:
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    if guild not in GUILDS:
        raise ValueError("unknown microbial guild")
    result = _copy_checked(state)
    if habitat_id not in result["habitats"]:
        raise ValueError("unknown inoculum habitat")
    source = _text(source, "inoculum source")
    population = _new_population(guild, biomass_kg, f"m48-{result['seed']}-{result['revision']}-{guild}", source, traits)
    if population["strain_id"] in result["habitats"][habitat_id]["populations"]:
        raise ValueError("strain identity collision")
    result["habitats"][habitat_id]["populations"][population["strain_id"]] = population
    # Explicit M48 inoculation is a boundary import; M03-owned biomass is
    # already present in the adapted initial ledger and is never counted twice.
    result["ledgers"]["organic_boundary_kg"] += float(biomass_kg)
    result["revision"] += 1
    result["transfer_events"].append({"kind": "inoculum", "target_habitat": habitat_id, "strain_id": population["strain_id"], "biomass_kg": float(biomass_kg), "source_id": source})
    result["transfer_events"] = result["transfer_events"][-MAX_EVENTS:]
    validate(result)
    return result


def disperse(state: Mapping[str, Any], source_habitat: str, target_habitat: str, biomass_kg: float, strain_id: str | None = None, guild: str | None = None, route_id: str | None = None, source_id: str = "declared-dispersal", expected_revision: int | None = None) -> dict[str, Any]:
    """Move finite viable biomass along one enabled connected route."""
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    if source_habitat not in result["habitats"] or target_habitat not in result["habitats"]:
        raise ValueError("unknown dispersal habitat")
    candidates = [route for route in result["routes"] if route["source_habitat"] == source_habitat and route["target_habitat"] == target_habitat and route["enabled"] and (route_id is None or route["route_id"] == route_id)]
    if not candidates:
        raise ValueError("no enabled connected dispersal route")
    route = candidates[0]
    if route["sealed_blocked"]:
        raise ValueError("route is blocked by a seal")
    amount = _number(biomass_kg, "dispersal biomass")
    source_key, source = _find_population(result["habitats"][source_habitat], strain_id, guild)
    if source["biomass_kg"] + EPSILON < amount:
        raise ValueError("dispersal exceeds viable source biomass")
    if route["used_kg"] + amount > route["capacity_kg"] + EPSILON:
        raise ValueError("dispersal exceeds finite route capacity")
    target_pops = result["habitats"][target_habitat]["populations"]
    target = target_pops.get(source_key)
    if target is None:
        target = copy.deepcopy(source)
        target["biomass_kg"] = 0.0
        target["reserves_kg"] = 0.0
        target["nutrients"] = _nutrients()
        target["inoculum_sources"] = []
        target_pops[source_key] = target
    fraction = 0.0 if source["biomass_kg"] <= EPSILON else amount / source["biomass_kg"]
    source["biomass_kg"] -= amount
    reserve = source["reserves_kg"] * fraction
    source["reserves_kg"] -= reserve
    target["biomass_kg"] += amount
    target["reserves_kg"] += reserve
    for nutrient in NUTRIENTS:
        moved = source["nutrients"][nutrient] * fraction
        source["nutrients"][nutrient] -= moved
        target["nutrients"][nutrient] += moved
    target["inoculum_sources"] = list(dict.fromkeys((target["inoculum_sources"] + [_text(source_id, "source_id")])))[-16:]
    target["activity"] = "active"
    source["activity"] = "dormant" if source["biomass_kg"] <= EPSILON else source["activity"]
    route["used_kg"] += amount
    result["revision"] += 1
    result["transfer_events"].append({"kind": "dispersal", "route_id": route["route_id"], "source_habitat": source_habitat, "target_habitat": target_habitat, "strain_id": source_key, "biomass_kg": amount, "source_id": source_id})
    result["transfer_events"] = result["transfer_events"][-MAX_EVENTS:]
    validate(result)
    return result


transfer = disperse


def set_mutation(state: Mapping[str, Any], habitat_id: str, strain_id: str, enabled: bool, mutation_rate: float | None = None, expected_revision: int | None = None) -> dict[str, Any]:
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    population = result["habitats"].get(habitat_id, {}).get("populations", {}).get(strain_id)
    if population is None:
        raise ValueError("unknown strain")
    population["traits"]["mutation_enabled"] = bool(enabled)
    if mutation_rate is not None:
        population["traits"]["mutation_rate"] = _number(mutation_rate, "mutation_rate", 0.0, 0.25)
    result["revision"] += 1
    validate(result)
    return result


def mutate_strain(state: Mapping[str, Any], habitat_id: str, strain_id: str, trait_deltas: Mapping[str, Any] | None = None, biomass_fraction: float = 0.25, expected_revision: int | None = None) -> dict[str, Any]:
    """Create a bounded heritable offspring strain while retaining an ancestor control."""
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    habitat = result["habitats"].get(habitat_id)
    if habitat is None or strain_id not in habitat["populations"]:
        raise ValueError("unknown strain")
    parent = habitat["populations"][strain_id]
    if not parent["traits"]["mutation_enabled"]:
        raise ValueError("mutation is disabled for this strain")
    fraction = _number(biomass_fraction, "biomass_fraction", 0.0, 1.0)
    child_biomass = parent["biomass_kg"] * fraction
    if child_biomass <= EPSILON:
        raise ValueError("mutation needs viable parent biomass")
    child_traits = dict(parent["traits"])
    for key, value in (trait_deltas or {}).items():
        if key not in {"uptake_affinity", "maintenance_multiplier", "temperature_tolerance", "mutation_rate"}:
            raise ValueError("unsupported bounded trait")
        child_traits[key] = float(child_traits[key]) + float(value)
    child_traits = _traits(child_traits)
    parent["biomass_kg"] -= child_biomass
    child_lineage = f"{parent['lineage_id']}.g{parent['generation'] + 1}.m{parent['mutation_events'] + 1}"
    child = _new_population(parent["guild"], child_biomass, child_lineage, "mutation", child_traits, strain_id, parent["generation"] + 1)
    child["ancestor_control"] = copy.deepcopy(parent["ancestor_control"])
    child["mutation_events"] = parent["mutation_events"] + 1
    parent["mutation_events"] += 1
    habitat["populations"][child["strain_id"]] = child
    result["revision"] += 1
    validate(result)
    return result


def ancestor_control(state: Mapping[str, Any], habitat_id: str, strain_id: str) -> dict[str, Any]:
    validate(state)
    population = state["habitats"].get(habitat_id, {}).get("populations", {}).get(strain_id)
    if population is None:
        raise ValueError("unknown strain")
    return copy.deepcopy(population["ancestor_control"])


def _environment_factor(habitat: Mapping[str, Any], guild: str, traits: Mapping[str, Any]) -> float:
    spec = m03.GUILD_SPECS[guild]
    env = habitat["environment"]
    tolerance = traits["temperature_tolerance"]
    temp_width = spec["temperature_width_c"] * tolerance
    temperature = math.exp(-((env["temperature_c"] - spec["temperature_optimum_c"]) / temp_width) ** 2)
    moisture = max(0.0, 1.0 - abs(env["moisture"] - spec["moisture_optimum"]) / spec["moisture_width"])
    oxygen = math.exp(-((env["oxygen"] - spec["oxygen_optimum"]) / spec["oxygen_width"]) ** 2)
    return _clamp(temperature * moisture * oxygen, 0.0, 1.0)


def _best_substrate(habitat: Mapping[str, Any], guild: str) -> str | None:
    allowed = m03.GUILD_SPECS[guild]["substrates"]
    options = [(name, record) for name, record in habitat["substrates"].items() if name in allowed and record["mass_kg"] > EPSILON]
    return max(options, key=lambda pair: pair[1]["mass_kg"] * pair[1]["accessibility"])[0] if options else None


def _consume(habitat: dict[str, Any], population: dict[str, Any], amount: float, substrate_name: str) -> float:
    record = habitat["substrates"][substrate_name]
    amount = min(amount, record["mass_kg"])
    before = record["mass_kg"]
    fraction = 0.0 if before <= EPSILON else amount / before
    nutrient_take = {key: record["nutrients"][key] * fraction for key in NUTRIENTS}
    record["mass_kg"] -= amount
    for key in NUTRIENTS:
        record["nutrients"][key] -= nutrient_take[key]
        population["nutrients"][key] += nutrient_take[key] * 0.7
        habitat["available_nutrients"][key] += nutrient_take[key] * 0.3
    return amount


def _step_ecology(result: dict[str, Any], dt_s: float) -> None:
    dt_days = dt_s / 86400.0
    for habitat in result["habitats"].values():
        demands: dict[str, tuple[str, float]] = {}
        for strain_id, population in habitat["populations"].items():
            if population["biomass_kg"] <= EPSILON:
                population["activity"] = "dormant"
                continue
            substrate_name = _best_substrate(habitat, population["guild"])
            if substrate_name is None:
                population["activity"] = "dormant"
                continue
            spec = m03.GUILD_SPECS[population["guild"]]
            env_factor = _environment_factor(habitat, population["guild"], population["traits"])
            demand = population["biomass_kg"] * spec["uptake_per_day"] * env_factor * population["traits"]["uptake_affinity"] * dt_days
            demands[strain_id] = (substrate_name, max(0.0, demand))
        grouped: dict[str, list[tuple[str, float]]] = {}
        for strain_id, (substrate_name, demand) in demands.items():
            grouped.setdefault(substrate_name, []).append((strain_id, demand))
        for substrate_name, members in grouped.items():
            available = habitat["substrates"][substrate_name]["mass_kg"]
            total_demand = sum(demand for _, demand in members)
            if total_demand <= EPSILON:
                continue
            for strain_id, demand in members:
                amount = min(demand, available * demand / total_demand)
                population = habitat["populations"][strain_id]
                env_factor = _environment_factor(habitat, population["guild"], population["traits"])
                consumed = _consume(habitat, population, amount, substrate_name)
                spec = m03.GUILD_SPECS[population["guild"]]
                gain = consumed * spec["yield"] * 0.72
                reserve_gain = consumed * spec["yield"] * 0.12
                population["biomass_kg"] += gain
                population["reserves_kg"] += reserve_gain
                product = max(0.0, consumed - gain - reserve_gain)
                product_key = "fermentation_products_kg" if population["guild"] == "yeast_fermenter" else "acids_kg" if population["guild"] == "acid_producer" else "co2_kg"
                habitat["byproducts"].setdefault(product_key, 0.0)
                habitat["byproducts"][product_key] += product
                population["division_progress"] += gain / max(population["biomass_kg"], 0.001)
                divisions = int(population["division_progress"])
                if divisions:
                    population["division_events"] += divisions
                    population["division_progress"] -= divisions
                if population["traits"]["mutation_enabled"] and population["traits"]["mutation_rate"] > 0 and divisions:
                    population["mutation_events"] += 1
                maintenance = (population["biomass_kg"] + population["reserves_kg"]) * spec["maintenance_per_day"] * population["traits"]["maintenance_multiplier"] * dt_days
                used = min(population["reserves_kg"], maintenance)
                population["reserves_kg"] -= used
                biomass_used = 0.0
                if maintenance > used:
                    biomass_used = min(population["biomass_kg"], maintenance - used)
                    population["biomass_kg"] = max(0.0, population["biomass_kg"] - biomass_used)
                habitat["byproducts"].setdefault("co2_kg", 0.0)
                habitat["byproducts"]["co2_kg"] += used + biomass_used
                population["activity"] = "active" if env_factor >= 0.04 and (consumed > EPSILON or population["reserves_kg"] > EPSILON) else "dormant"
        for population in habitat["populations"].values():
            if population["biomass_kg"] <= EPSILON:
                population["biomass_kg"] = 0.0
                population["activity"] = "dormant"


def _fermentation_factor(process: Mapping[str, Any]) -> float:
    temperature = math.exp(-((process["temperature_c"] - 25.0) / 16.0) ** 2)
    oxygen = 0.45 + 0.55 * math.exp(-((process["oxygen"] - 0.25) / 0.65) ** 2)
    return _clamp(temperature * oxygen, 0.0, 1.0)


def start_fermentation(state: Mapping[str, Any], container_id: str, substrate: str = "food", substrate_mass_kg: float | None = None, culture_strain_id: str | None = None, culture_guild: str = "yeast_fermenter", capacity_kg: float | None = None, gas_capacity_kg: float = 0.05, sealed: bool = True, vented: bool = False, temperature_c: float | None = None, oxygen: float | None = None, expected_revision: int | None = None) -> dict[str, Any]:
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    habitat = result["habitats"].get(container_id)
    if habitat is None or habitat["kind"] != "container":
        raise ValueError("fermentation requires a container habitat")
    if culture_guild not in GUILDS:
        raise ValueError("unknown culture guild")
    record = habitat["substrates"].get(substrate)
    if record is None:
        raise ValueError("container lacks requested substrate")
    amount = record["mass_kg"] if substrate_mass_kg is None else _number(substrate_mass_kg, "fermentation substrate mass")
    if amount > record["mass_kg"] + EPSILON:
        raise ValueError("fermentation exceeds finite substrate")
    source_id, culture = _find_population(habitat, culture_strain_id, culture_guild)
    culture_amount = culture["biomass_kg"]
    if culture_amount <= EPSILON:
        raise ValueError("fermentation requires a declared viable culture")
    if capacity_kg is None:
        capacity_kg = amount + culture_amount
    capacity_kg = _number(capacity_kg, "container capacity")
    gas_capacity_kg = _number(gas_capacity_kg, "gas capacity")
    if amount + culture_amount > capacity_kg + EPSILON:
        raise ValueError("container capacity exceeded")
    record["mass_kg"] -= amount
    culture["biomass_kg"] -= culture_amount
    culture["activity"] = "dormant"
    process_id = f"fermentation-{result['revision']}-{container_id}"
    process = {
        "process_id": process_id,
        "container_id": container_id,
        "substrate": substrate,
        "culture_strain_id": source_id,
        "sealed": bool(sealed),
        "vented": bool(vented),
        "capacity_kg": capacity_kg,
        "gas_capacity_kg": gas_capacity_kg,
        "temperature_c": _number(temperature_c if temperature_c is not None else habitat["environment"]["temperature_c"], "fermentation temperature", -80.0, 100.0),
        "oxygen": _number(oxygen if oxygen is not None else habitat["environment"]["oxygen"], "fermentation oxygen", 0.0, 1.0),
        "substrate_mass_kg": amount,
        "culture_biomass_kg": culture_amount,
        "product_mass_kg": 0.0,
        "byproduct_mass_kg": 0.0,
        "gas_mass_kg": 0.0,
        "exported_mass_kg": 0.0,
        "elapsed_s": 0.0,
        "status": "active",
        "events": [],
    }
    result["fermentations"][process_id] = process
    result["revision"] += 1
    validate(result)
    return result


ferment = start_fermentation


def _step_fermentation(process: dict[str, Any], dt_s: float, result: dict[str, Any]) -> None:
    if process["status"] != "active" or process["substrate_mass_kg"] <= EPSILON:
        process["status"] = "complete" if process["substrate_mass_kg"] <= EPSILON else process["status"]
        return
    factor = _fermentation_factor(process)
    requested = min(process["substrate_mass_kg"], process["culture_biomass_kg"] * 0.55 * factor * dt_s / 86400.0)
    gas_share = 0.10
    if process["sealed"] and not process["vented"]:
        requested = min(requested, max(0.0, process["gas_capacity_kg"] - process["gas_mass_kg"]) / gas_share)
    if requested <= EPSILON:
        process["status"] = "blocked_sealed_gas" if process["sealed"] and not process["vented"] else "dormant"
        return
    process["substrate_mass_kg"] -= requested
    process["culture_biomass_kg"] += requested * 0.10
    process["product_mass_kg"] += requested * 0.60
    process["byproduct_mass_kg"] += requested * 0.20
    generated_gas = requested * gas_share
    if process["vented"]:
        process["exported_mass_kg"] += generated_gas
        result["ledgers"]["organic_boundary_kg"] -= generated_gas
    else:
        process["gas_mass_kg"] += generated_gas
    if process["sealed"]:
        process["oxygen"] = max(0.0, process["oxygen"] - requested * 0.02)
    else:
        process["oxygen"] = _clamp(process["oxygen"] + (0.21 - process["oxygen"]) * min(1.0, dt_s / 86400.0), 0.0, 1.0)
    process["elapsed_s"] += dt_s
    process["events"].append({"dt_s": dt_s, "substrate_consumed_kg": requested, "product_kg": requested * 0.60, "byproduct_kg": requested * 0.20, "gas_kg": generated_gas, "vented": process["vented"]})
    process["events"] = process["events"][-MAX_EVENTS:]
    if process["substrate_mass_kg"] <= EPSILON:
        process["substrate_mass_kg"] = 0.0
        process["status"] = "complete"


def step(state: Mapping[str, Any], dt_s: float, expected_revision: int | None = None) -> dict[str, Any]:
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    dt_s = _number(dt_s, "step dt_s", 0.0, MAX_STEP_S)
    result = _copy_checked(state)
    remaining = dt_s
    while remaining > EPSILON:
        substep = min(3600.0, remaining)
        _step_ecology(result, substep)
        for process in result["fermentations"].values():
            _step_fermentation(process, substep, result)
        result["time_s"] += substep
        remaining -= substep
    result["revision"] += 1
    validate(result)
    return result


fermentation_step = step


def to_microcosm(state: Mapping[str, Any], habitat_id: str, max_cells: int = 32) -> dict[str, Any]:
    """Return a detached observer representation; it is never an ecology owner."""
    validate(state)
    max_cells = int(_number(max_cells, "max_cells", 1, MAX_MICROCOSM_CELLS))
    habitat = state["habitats"].get(habitat_id)
    if habitat is None:
        raise ValueError("unknown microcosm habitat")
    cells = []
    for population in habitat["populations"].values():
        count = min(max_cells - len(cells), max(1, int(round(population["biomass_kg"] * 10))))
        for index in range(max(0, count)):
            cells.append({"cell_id": f"{population['strain_id']}:{index}", "strain_id": population["strain_id"], "biomass_kg": population["biomass_kg"] / count if count else 0.0})
            if len(cells) >= max_cells:
                break
        if len(cells) >= max_cells:
            break
    return {
        "rule": "alice.micro-ecology.observer-microcosm/v1",
        "representation_only": True,
        "habitat_id": habitat_id,
        "stocks": {"substrates": copy.deepcopy(habitat["substrates"]), "populations": {key: {"biomass_kg": value["biomass_kg"], "reserves_kg": value["reserves_kg"]} for key, value in habitat["populations"].items()}},
        "cells": cells,
        "source_state_hash": state_hash(state),
    }


def from_microcosm(state: Mapping[str, Any], microcosm: Mapping[str, Any]) -> dict[str, Any]:
    """Round-trip validation for observer conversion; returns unchanged ecology."""
    validate(state)
    if microcosm.get("representation_only") is not True or microcosm.get("habitat_id") not in state["habitats"]:
        raise ValueError("invalid observer microcosm")
    habitat = state["habitats"][microcosm["habitat_id"]]
    if microcosm.get("stocks", {}).get("substrates") != habitat["substrates"]:
        raise ValueError("microcosm substrate stocks changed")
    expected_populations = {key: {"biomass_kg": value["biomass_kg"], "reserves_kg": value["reserves_kg"]} for key, value in habitat["populations"].items()}
    if microcosm.get("stocks", {}).get("populations") != expected_populations:
        raise ValueError("microcosm population stocks changed")
    return copy.deepcopy(dict(state))


observer_microcosm = to_microcosm
aggregate_from_microcosm = from_microcosm


def inspect(state: Mapping[str, Any]) -> dict[str, Any]:
    validate(state)
    return {
        "rule": RULE,
        "version": VERSION,
        "revision": state["revision"],
        "time_s": state["time_s"],
        "habitats": [{"habitat_id": hid, "kind": habitat["kind"], "substrate_mass_kg": sum(record["mass_kg"] for record in habitat["substrates"].values()), "strains": {key: {"guild": value["guild"], "biomass_kg": value["biomass_kg"], "traits": copy.deepcopy(value["traits"]), "ancestor_id": value["ancestor_id"]} for key, value in habitat["populations"].items()}} for hid, habitat in state["habitats"].items()],
        "fermentations": copy.deepcopy(state["fermentations"]),
        "disease": {"status": "disabled"},
        "tracked_organic_kg": _total_organic(state),
        "state_hash": state_hash(state),
    }


def save(state: Mapping[str, Any], path: str | Path) -> dict[str, Any]:
    validate(state)
    destination = Path(path)
    if destination.exists():
        raise ValueError("refuse overwriting an ecology checkpoint")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = copy.deepcopy(dict(state))
    payload["state_hash"] = state_hash(state)
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(_canonical(payload) + "\n")
    return {"path": str(destination), "state_hash": payload["state_hash"], "revision": state["revision"]}


def resume(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    recorded = payload.pop("state_hash", None)
    if recorded != state_hash(payload):
        raise ValueError("M48 checkpoint checksum mismatch")
    validate(payload)
    return payload


def replay(state: Mapping[str, Any], commands: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result = _copy_checked(state)
    for command in commands:
        _reject_forbidden(command, "command")
        kind = command.get("kind")
        if kind == "step":
            result = step(result, command["dt_s"])
        elif kind == "add_route":
            result = add_route(result, command)
        elif kind == "inoculate":
            result = inoculate_strain(result, command["habitat_id"], command["guild"], command["biomass_kg"], command.get("source", "replay"), command.get("traits"))
        elif kind == "disperse":
            result = disperse(result, command["source_habitat"], command["target_habitat"], command["biomass_kg"], command.get("strain_id"), command.get("guild"), command.get("route_id"), command.get("source_id", "replay"))
        elif kind == "set_mutation":
            result = set_mutation(result, command["habitat_id"], command["strain_id"], command["enabled"], command.get("mutation_rate"))
        elif kind == "mutate":
            result = mutate_strain(result, command["habitat_id"], command["strain_id"], command.get("trait_deltas"), command.get("biomass_fraction", 0.25))
        elif kind == "fermentation_start":
            result = start_fermentation(result, **{key: value for key, value in command.items() if key != "kind"})
        else:
            raise ValueError(f"unknown M48 replay command: {kind}")
    return result


__all__ = [
    "RULE", "VERSION", "GUILDS", "EcologyConflictError", "adapt_m03", "initial_from_m03", "validate", "state_hash", "add_route", "inoculate_strain", "disperse", "transfer", "set_mutation", "mutate_strain", "ancestor_control", "start_fermentation", "ferment", "step", "fermentation_step", "to_microcosm", "from_microcosm", "observer_microcosm", "aggregate_from_microcosm", "inspect", "save", "resume", "replay",
]
