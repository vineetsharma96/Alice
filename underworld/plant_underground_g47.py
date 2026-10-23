"""Bounded, additive Alice 01 G4-G7 plant and shallow-underground sidecar.

The sidecar consumes a copy of a G0-G3 manifest and never mutates that manifest,
the native world, storage.py, or existing saves.  Values are deliberately declared
engineering abstractions: biomass is dry matter in kg, seed reserve is dry matter
in kg, soil resource factors are bounded unitless values, and excavated material is
mass derived from the source manifest's material density.

G4-G7 are represented as JSON-compatible dictionaries so a state can be copied,
saved, resumed, and replayed without dictionary-order or rendering dependencies.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

from .world_generation_g01 import MATERIALS, manifest_hash, validate_manifest


CONTRACT_VERSION = "alice.plant-underground.g47/v1"
G47_VERSION = "g47.2"
EPSILON = 1e-9


class ConflictError(ValueError):
    """Raised when a copy-on-write operation used an old sidecar revision."""


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _finite(value: Any, label: str, low: float = 0.0, high: float = float("inf")) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if result < low or result > high:
        raise ValueError(f"{label} must be in [{low}, {high}]")
    return result


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def state_hash(state: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(state))
    body.pop("state_hash", None)
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _stream(seed: int, domain: str, *parts: Any) -> float:
    payload = "|".join([str(int(seed)), domain, *(str(p) for p in parts)]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") / 2**64


def _coord_key(x: int, y: int) -> str:
    return f"{int(x)},{int(y)}"


# Fictional ecological analogues.  Rates are design constants, not real botany.
# Each record has meaningful habitat, allocation, reproductive, and morphology data.
SPECIES: dict[str, dict[str, Any]] = {
    "sunspire_tree": {"functional_group": "tree", "strategy": "light_demanding_fast", "moisture": (0.35, 0.8), "shade_tolerance": 0.22, "root_depth_m": 1.8, "nutrient_need": 0.58, "growth_rate_kg_day": 0.38, "max_biomass_kg": 85.0, "seed_mass_kg": 0.012, "seed_cost_kg": 0.025, "seed_production": 8, "mature_days": 24.0, "lifespan_days": 5000.0, "reproductive_start_days": 36.0, "flower_window": (70, 110), "pollination": "animal", "dispersal": "gravity", "coppice": False, "root_reserve_fraction": 0.18, "leaf_shape": "narrow", "flower_color": "amber"},
    "deepshade_tree": {"functional_group": "tree", "strategy": "shade_tolerant_slow", "moisture": (0.3, 0.9), "shade_tolerance": 0.9, "root_depth_m": 2.4, "nutrient_need": 0.42, "growth_rate_kg_day": 0.16, "max_biomass_kg": 110.0, "seed_mass_kg": 0.016, "seed_cost_kg": 0.02, "seed_production": 6, "mature_days": 42.0, "lifespan_days": 7000.0, "reproductive_start_days": 58.0, "flower_window": (150, 205), "pollination": "wind", "dispersal": "wind", "coppice": True, "root_reserve_fraction": 0.3, "leaf_shape": "broad", "flower_color": "ivory"},
    "stoneleaf_tree": {"functional_group": "tree", "strategy": "dry_adapted", "moisture": (0.12, 0.58), "shade_tolerance": 0.36, "root_depth_m": 2.8, "nutrient_need": 0.3, "growth_rate_kg_day": 0.21, "max_biomass_kg": 72.0, "seed_mass_kg": 0.01, "seed_cost_kg": 0.018, "seed_production": 7, "mature_days": 38.0, "lifespan_days": 6200.0, "reproductive_start_days": 52.0, "flower_window": (245, 300), "pollination": "wind", "dispersal": "gravity", "coppice": True, "root_reserve_fraction": 0.34, "leaf_shape": "succulent", "flower_color": "red"},
    "fruiting_brush": {"functional_group": "shrub", "strategy": "fruiting_shrub", "moisture": (0.3, 0.82), "shade_tolerance": 0.5, "root_depth_m": 0.8, "nutrient_need": 0.62, "growth_rate_kg_day": 0.2, "max_biomass_kg": 18.0, "seed_mass_kg": 0.006, "seed_cost_kg": 0.01, "seed_production": 10, "mature_days": 18.0, "lifespan_days": 900.0, "reproductive_start_days": 28.0, "flower_window": (90, 160), "pollination": "animal", "dispersal": "animal", "coppice": True, "root_reserve_fraction": 0.28, "leaf_shape": "oval", "flower_color": "violet"},
    "shelter_brush": {"functional_group": "shrub", "strategy": "non_fruiting_shelter", "moisture": (0.22, 0.72), "shade_tolerance": 0.7, "root_depth_m": 0.7, "nutrient_need": 0.35, "growth_rate_kg_day": 0.15, "max_biomass_kg": 22.0, "seed_mass_kg": 0.004, "seed_cost_kg": 0.008, "seed_production": 5, "mature_days": 20.0, "lifespan_days": 1200.0, "reproductive_start_days": 32.0, "flower_window": (180, 250), "pollination": "wind", "dispersal": "wind", "coppice": True, "root_reserve_fraction": 0.3, "leaf_shape": "serrated", "flower_color": "white"},
    "meadow_grass": {"functional_group": "grass", "strategy": "fast_groundcover", "moisture": (0.25, 0.85), "shade_tolerance": 0.42, "root_depth_m": 0.35, "nutrient_need": 0.3, "growth_rate_kg_day": 0.11, "max_biomass_kg": 3.5, "seed_mass_kg": 0.001, "seed_cost_kg": 0.002, "seed_production": 16, "mature_days": 10.0, "lifespan_days": 280.0, "reproductive_start_days": 16.0, "flower_window": (30, 330), "pollination": "wind", "dispersal": "wind", "coppice": False, "root_reserve_fraction": 0.12, "leaf_shape": "blade", "flower_color": "green"},
    "river_reed": {"functional_group": "herb", "strategy": "wet_ground", "moisture": (0.62, 1.0), "shade_tolerance": 0.5, "root_depth_m": 0.55, "nutrient_need": 0.46, "growth_rate_kg_day": 0.13, "max_biomass_kg": 5.0, "seed_mass_kg": 0.0015, "seed_cost_kg": 0.002, "seed_production": 12, "mature_days": 12.0, "lifespan_days": 340.0, "reproductive_start_days": 18.0, "flower_window": (100, 220), "pollination": "wind", "dispersal": "water", "coppice": False, "root_reserve_fraction": 0.14, "leaf_shape": "spear", "flower_color": "gold"},
    "bluebell_annual": {"functional_group": "flower", "strategy": "annual_meadow", "moisture": (0.28, 0.72), "shade_tolerance": 0.28, "root_depth_m": 0.18, "nutrient_need": 0.35, "growth_rate_kg_day": 0.045, "max_biomass_kg": 0.7, "seed_mass_kg": 0.0004, "seed_cost_kg": 0.0007, "seed_production": 24, "mature_days": 7.0, "lifespan_days": 120.0, "reproductive_start_days": 10.0, "flower_window": (45, 95), "pollination": "animal", "dispersal": "animal", "coppice": False, "root_reserve_fraction": 0.05, "leaf_shape": "round", "flower_color": "blue"},
    "sunpetal_perennial": {"functional_group": "flower", "strategy": "perennial", "moisture": (0.35, 0.8), "shade_tolerance": 0.5, "root_depth_m": 0.3, "nutrient_need": 0.48, "growth_rate_kg_day": 0.04, "max_biomass_kg": 1.0, "seed_mass_kg": 0.0005, "seed_cost_kg": 0.0008, "seed_production": 18, "mature_days": 12.0, "lifespan_days": 520.0, "reproductive_start_days": 22.0, "flower_window": (110, 180), "pollination": "animal", "dispersal": "gravity", "coppice": False, "root_reserve_fraction": 0.12, "leaf_shape": "lance", "flower_color": "yellow"},
    "froststar_early": {"functional_group": "flower", "strategy": "early_season", "moisture": (0.3, 0.7), "shade_tolerance": 0.58, "root_depth_m": 0.2, "nutrient_need": 0.3, "growth_rate_kg_day": 0.038, "max_biomass_kg": 0.8, "seed_mass_kg": 0.00035, "seed_cost_kg": 0.0007, "seed_production": 20, "mature_days": 11.0, "lifespan_days": 430.0, "reproductive_start_days": 18.0, "flower_window": (1, 48), "pollination": "wind", "dispersal": "wind", "coppice": False, "root_reserve_fraction": 0.1, "leaf_shape": "star", "flower_color": "white"},
    "emberlate_lily": {"functional_group": "flower", "strategy": "late_season", "moisture": (0.4, 0.78), "shade_tolerance": 0.35, "root_depth_m": 0.22, "nutrient_need": 0.4, "growth_rate_kg_day": 0.042, "max_biomass_kg": 0.9, "seed_mass_kg": 0.00045, "seed_cost_kg": 0.0008, "seed_production": 21, "mature_days": 13.0, "lifespan_days": 390.0, "reproductive_start_days": 270.0, "flower_window": (270, 335), "pollination": "animal", "dispersal": "animal", "coppice": False, "root_reserve_fraction": 0.08, "leaf_shape": "lily", "flower_color": "orange"},
    "marshbell_wet": {"functional_group": "flower", "strategy": "wet_ground", "moisture": (0.68, 1.0), "shade_tolerance": 0.52, "root_depth_m": 0.24, "nutrient_need": 0.52, "growth_rate_kg_day": 0.04, "max_biomass_kg": 0.85, "seed_mass_kg": 0.0005, "seed_cost_kg": 0.0009, "seed_production": 17, "mature_days": 14.0, "lifespan_days": 400.0, "reproductive_start_days": 210.0, "flower_window": (190, 260), "pollination": "wind", "dispersal": "water", "coppice": False, "root_reserve_fraction": 0.1, "leaf_shape": "heart", "flower_color": "pink"},
    "dustcup_dry": {"functional_group": "flower", "strategy": "dry_ground", "moisture": (0.08, 0.5), "shade_tolerance": 0.18, "root_depth_m": 0.2, "nutrient_need": 0.22, "growth_rate_kg_day": 0.043, "max_biomass_kg": 0.75, "seed_mass_kg": 0.0004, "seed_cost_kg": 0.0007, "seed_production": 19, "mature_days": 10.0, "lifespan_days": 300.0, "reproductive_start_days": 230.0, "flower_window": (220, 285), "pollination": "wind", "dispersal": "wind", "coppice": False, "root_reserve_fraction": 0.06, "leaf_shape": "cup", "flower_color": "magenta"},
}


def species_catalog() -> dict[str, dict[str, Any]]:
    """Return a deep copy of the data-driven functional catalog."""
    return copy.deepcopy(SPECIES)


def _cell(manifest: Mapping[str, Any], x: int, y: int) -> Mapping[str, Any]:
    for cell in manifest["cells"]:
        if cell["coord"] == {"x": int(x), "y": int(y)}:
            return cell
    raise KeyError((x, y))


def _layer_mass(material_id: str, volume_m3: float, manifest: Mapping[str, Any]) -> float:
    materials = manifest.get("materials", MATERIALS)
    return float(volume_m3) * float(materials[material_id]["density_kg_m3"])


def _next_id(state: Mapping[str, Any], prefix: str) -> str:
    return f"{prefix}-{state['revision'] + 1}-{len(state.get(prefix + 's', [])) + 1}"


def _initial_species(seed: int, cell: Mapping[str, Any], index: int) -> str:
    available = ("sunspire_tree", "deepshade_tree", "stoneleaf_tree", "fruiting_brush", "shelter_brush", "meadow_grass", "river_reed", "bluebell_annual", "sunpetal_perennial", "froststar_early", "emberlate_lily", "marshbell_wet", "dustcup_dry")
    return available[int(_stream(seed, "initial-species", cell["coord"]["x"], cell["coord"]["y"], index) * len(available)) % len(available)]


def _plant_record(state_seed: int, plant_id: str, species_id: str, x: int, y: int, index: int, stage: str = "juvenile") -> dict[str, Any]:
    traits = SPECIES[species_id]
    mature = float(traits["mature_days"])
    age = mature * (0.55 + 0.25 * _stream(state_seed, "plant-age", plant_id)) if stage == "adult" else mature * 0.2
    biomass = min(float(traits["max_biomass_kg"]), max(0.01, float(traits["max_biomass_kg"]) * (0.2 if stage != "adult" else 0.62) * (0.8 + 0.2 * _stream(state_seed, "plant-biomass", plant_id))))
    return {"plant_id": plant_id, "species_id": species_id, "coord": {"x": x, "y": y}, "stage": stage, "age_days": round(age, 8), "biomass_kg": round(biomass, 8), "reserve_kg": round(biomass * float(traits["root_reserve_fraction"]), 8), "seed_supply": 0, "flowered": False, "pollinated": False, "alive": True, "stump": False, "individual_index": index}


def initialize(manifest: Mapping[str, Any], initial_plants: int | None = None) -> dict[str, Any]:
    """Create an independent G4-G7 state from a validated G0-G3 manifest."""
    validate_manifest(manifest)
    seed = int(manifest["seed"])
    plants: list[dict[str, Any]] = []
    seed_banks: dict[str, list[dict[str, Any]]] = {}
    underground_cells: dict[str, dict[str, Any]] = {}
    material_stocks: dict[str, dict[str, float]] = {}
    for material in MATERIALS:
        material_stocks[material] = {"initial_kg": 0.0, "available_kg": 0.0, "extracted_kg": 0.0, "loose_kg": 0.0, "spoil_kg": 0.0, "hauled_kg": 0.0, "deposited_kg": 0.0}
    for cell_index, source_cell in enumerate(manifest["cells"]):
        x, y = source_cell["coord"]["x"], source_cell["coord"]["y"]
        key = _coord_key(x, y)
        lots = []
        for source_seed in source_cell.get("plant_seeds", []):
            lots.append({"seed_lot_id": source_seed["seed_lot_id"], "species_id": source_seed["species_id"] if source_seed["species_id"] in SPECIES else "meadow_grass", "count": 1, "viability": float(source_seed.get("viability", 0.7)), "reserve_mass_kg": float(source_seed.get("reserve_mass_kg", 0.002)), "age_days": 0.0, "origin": "g01_seed_bank", "dormant": False})
        seed_banks[key] = lots
        layers = []
        for horizon in source_cell.get("horizons", []):
            material = horizon["material_id"]
            volume = float(horizon["volume_m3"])
            mass = _layer_mass(material, volume, manifest)
            layers.append({"layer_id": horizon["layer_id"], "material_id": material, "initial_volume_m3": round(volume, 8), "remaining_volume_m3": round(volume, 8), "depth_m": round(sum(float(h["thickness_m"]) for h in source_cell["horizons"][:len(layers)]), 8), "occupied": False, "exposed": horizon["layer_id"] == source_cell.get("exposed_layer_id", "O"), "support_required": False})
            material_stocks[material]["initial_kg"] += mass
            material_stocks[material]["available_kg"] += mass
        underground_cells[key] = {"coord": {"x": x, "y": y}, "layers": layers, "surface_occupied": False, "open_nodes": [], "water_risk": bool(source_cell.get("standing_water", False))}
        count = int(initial_plants if initial_plants is not None else (1 if source_cell.get("plant_condition", {}).get("waterlogged") is not True and _stream(seed, "plant-presence", x, y) < float(manifest["config"].get("vegetation_density", 0.5)) else 0))
        for index in range(max(0, min(4, count))):
            species_id = _initial_species(seed, source_cell, index)
            traits = SPECIES[species_id]
            moisture = float(source_cell.get("moisture", 0.5))
            if not (traits["moisture"][0] - 0.18 <= moisture <= traits["moisture"][1] + 0.18):
                species_id = "meadow_grass"
            stage = "adult" if _stream(seed, "initial-stage", x, y, index) < 0.35 else "juvenile"
            plants.append(_plant_record(seed, f"plant-{x}-{y}-{index}", species_id, x, y, index, stage))
    source_cells = {_coord_key(c["coord"]["x"], c["coord"]["y"]): copy.deepcopy(c) for c in manifest["cells"]}
    state: dict[str, Any] = {"contract_version": CONTRACT_VERSION, "g47_version": G47_VERSION, "source_manifest_hash": manifest_hash(manifest), "world_id": manifest["world_id"], "seed": seed, "revision": 0, "config": {"ecology_time_scale": "one day per dt_days", "seed_failure_consumes_seed": True, "pollinator_population": 0.62, "surface_scale_m": manifest["config"]["cell_scale_m"]}, "species_catalog": species_catalog(), "plants": plants, "seed_banks": seed_banks, "seed_inventory": [], "source_cells": source_cells, "plant_ledgers": {"growth": [], "flowering": [], "seed_transfers": [], "cuttings": [], "nutrients": []}, "underground": {"cells": underground_cells, "connectors": [], "supports": [], "occupancy": {}, "spoil": {}, "material_stocks": material_stocks, "hauls": [], "operations": []}, "diagnostics": {"abstractions": ["bounded habitat suitability", "individual plants with finite dry biomass and reserves", "seed-lot counts rather than millions of objects", "shallow strata copied from G01 horizons", "adjacency-only underground connectors", "support demand is a declared span/depth heuristic"]}}
    validate_state(state)
    state["state_hash"] = state_hash(state)
    return state


def _copy_mutate(state: Mapping[str, Any], expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    validate_state(state)
    if expected_revision is not None and int(state["revision"]) != int(expected_revision):
        raise ConflictError("sidecar revision is stale")
    if operation_id and any(op.get("operation_id") == operation_id for op in state["underground"].get("operations", [])):
        return copy.deepcopy(dict(state))
    result = copy.deepcopy(dict(state))
    result["revision"] += 1
    result.pop("state_hash", None)
    return result


def _already_applied(state: Mapping[str, Any], operation_id: str | None) -> bool:
    return bool(operation_id) and any(op.get("operation_id") == operation_id for op in state.get("underground", {}).get("operations", []))


def _finish(state: dict[str, Any]) -> dict[str, Any]:
    validate_state(state)
    state["state_hash"] = state_hash(state)
    return state


def _site_factors(state: Mapping[str, Any], plant: Mapping[str, Any], rainfall_mm: float, shade_fraction: float, temperature_c: float, nutrient_factor: float) -> dict[str, float]:
    key = _coord_key(plant["coord"]["x"], plant["coord"]["y"])
    cell = state["_source_cells"][key] if "_source_cells" in state else None
    moisture = float(cell.get("moisture", 0.5)) if cell else 0.5
    condition = cell.get("plant_condition", {}) if cell else {}
    water = _clamp(float(condition.get("water_factor", moisture)) + rainfall_mm / 100.0 - (0.035 * max(0.0, temperature_c - 18.0)))
    traits = state["species_catalog"][plant["species_id"]]
    low, high = traits["moisture"]
    moisture_fit = _clamp(1.0 - abs(moisture - (low + high) / 2.0) / max(0.05, (high - low) / 2.0))
    if moisture < low:
        moisture_fit *= _clamp(moisture / max(low, 0.05))
    if moisture > high:
        moisture_fit *= _clamp((1.0 - moisture) / max(1.0 - high, 0.05))
    light = _clamp(1.0 - float(shade_fraction) * (1.0 - float(traits["shade_tolerance"])))
    drought = 0.42 if water < 0.16 else 1.0
    return {"water": water, "moisture_fit": moisture_fit, "light": light, "nutrient": _clamp(nutrient_factor), "drought": drought, "growth_factor": _clamp(moisture_fit * light * _clamp(water * 1.35) * _clamp(nutrient_factor))}


def _source_snapshot(state: Mapping[str, Any], source_manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if source_manifest is not None:
        validate_manifest(source_manifest)
        if manifest_hash(source_manifest) != state["source_manifest_hash"]:
            raise ValueError("source manifest hash does not match sidecar")
        # A repeated reference to the immutable source must not restore spent
        # nutrients in this sidecar's persistent copy.
        return state.get('source_cells') or {_coord_key(c["coord"]["x"], c["coord"]["y"]): copy.deepcopy(c) for c in source_manifest["cells"]}
    return state.get("source_cells", {})


def plant_step(state: Mapping[str, Any], days: float = 1.0, rainfall_mm: float = 0.0, temperature_c: float = 15.0, daylight_fraction: float = 0.5, shade: Mapping[str, float] | None = None, nutrient_factor: Mapping[str, float] | None = None, source_manifest: Mapping[str, Any] | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    """Advance individual/cohort plants with finite resources and reproduction."""
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    days = _finite(days, "days", 0.0, 10000.0)
    rain = _finite(rainfall_mm, "rainfall_mm", 0.0, 1000.0)
    temp = _finite(temperature_c, "temperature_c", -80.0, 80.0)
    daylight = _finite(daylight_fraction, "daylight_fraction", 0.0, 1.0)
    result = _copy_mutate(state, expected_revision, operation_id)
    source = _source_snapshot(result, source_manifest)
    result["source_cells"] = source
    if days == 0:
        result['underground']['operations'].append({'operation_id':operation_id,'kind':'plant_step','revision':result['revision']})
        return _finish(result)
    shade = shade or {}
    nutrient_factor = nutrient_factor or {}
    growth_events, seed_events, nutrient_events = [], [], []
    for plant in result["plants"]:
        if not plant["alive"]:
            continue
        traits = result["species_catalog"][plant["species_id"]]
        key = _coord_key(plant["coord"]["x"], plant["coord"]["y"])
        factors = _site_factors(result, plant, rain, float(shade.get(key, 0.0)), temp, float(nutrient_factor.get(key, 1.0)))
        old_biomass = float(plant["biomass_kg"])
        plant["age_days"] = round(float(plant["age_days"]) + days, 8)
        growth = float(traits["growth_rate_kg_day"]) * days * factors["growth_factor"] * daylight
        reserve_use = 0.0
        if factors["drought"] < 1.0:
            reserve_use = min(float(plant["reserve_kg"]), (1.0 - factors["drought"]) * 0.018 * days)
            plant["reserve_kg"] = round(float(plant["reserve_kg"]) - reserve_use, 8)
            growth *= factors["drought"]
        added = min(max(0.0, growth), max(0.0, float(traits["max_biomass_kg"]) - old_biomass))
        horizons=source.get(key,{}).get('horizons',[])
        demand=float(traits['nutrient_need'])*0.08
        if demand>0:
            available={n:sum(float(h.get('nutrients_available',{}).get(n,0)) for h in horizons) for n in ('N','P','K')}
            added=min(added,min(available.values())/demand)
        uptake=added*demand
        for nutrient in ('N','P','K'):
            remaining=uptake
            for horizon in horizons:
                pool=horizon.get('nutrients_available',{})
                take=min(remaining,float(pool.get(nutrient,0)))
                pool[nutrient]=max(0.,float(pool.get(nutrient,0))-take)
                remaining=max(0.,remaining-take)
        plant["biomass_kg"] = round(old_biomass + added, 8)
        if plant["biomass_kg"] >= float(traits["mature_days"]) / max(1.0, float(traits["mature_days"])) * float(traits["max_biomass_kg"]) * 0.3 and plant["age_days"] >= float(traits["mature_days"]):
            plant["stage"] = "adult"
        if plant["age_days"] > float(traits["lifespan_days"]):
            plant["stage"] = "senescent"
            loss = min(float(plant["biomass_kg"]), 0.03 * days * float(plant["biomass_kg"]))
            plant["biomass_kg"] = round(float(plant["biomass_kg"]) - loss, 8)
            if plant["biomass_kg"] <= EPSILON:
                plant["alive"] = False
        uptake = added * float(traits["nutrient_need"]) * 0.08
        nutrient_events.append({"plant_id": plant["plant_id"], "NPK_units": round(uptake, 8), "source": "finite_site_pool_abstraction"})
        growth_events.append({"plant_id": plant["plant_id"], "days": days, "biomass_added_kg": round(added, 8), "reserve_used_kg": round(reserve_use, 8), "water_factor": round(factors["water"], 8), "light_factor": round(factors["light"], 8), "growth_factor": round(factors["growth_factor"], 8)})
        day_of_year = int((float(plant["age_days"]) + result["revision"]) % 365)
        start, end = traits["flower_window"]
        if plant["stage"] == "adult" and start <= day_of_year <= end and daylight > 0.25 and factors["growth_factor"] > 0.18:
            plant["flowered"] = True
            pollination = _clamp((0.68 if traits["pollination"] == "wind" else float(result["config"]["pollinator_population"])) * daylight * factors["light"])
            plant["pollinated"] = pollination >= 0.28 and _stream(result["seed"], "pollination", plant["plant_id"], int(plant["age_days"])) < pollination
            if plant["pollinated"] and float(plant["reserve_kg"]) >= float(traits["seed_cost_kg"]):
                reserve_cost = float(traits["seed_cost_kg"])
                plant["reserve_kg"] = round(float(plant["reserve_kg"]) - reserve_cost, 8)
                produced = max(1, int(float(traits["seed_production"]) * pollination))
                plant["seed_supply"] = int(plant["seed_supply"]) + produced
                seed_events.append({"kind": "seed_set", "plant_id": plant["plant_id"], "count": produced, "pollination": round(pollination, 8)})
    result["plant_ledgers"]["growth"].extend(growth_events)
    result["plant_ledgers"]["nutrients"].extend(nutrient_events)
    result["plant_ledgers"]["flowering"].extend(seed_events)
    # Age finite soil lots and perform bounded germination. A failed attempt consumes
    # one viable seed by contract, making drought/shade recruitment visible and finite.
    for key, lots in result["seed_banks"].items():
        x, y = (int(v) for v in key.split(","))
        cell = source.get(key, {})
        moisture = float(cell.get("moisture", 0.5))
        site_shade = float(shade.get(key, 0.0))
        for lot in lots:
            lot["age_days"] = round(float(lot["age_days"]) + days, 8)
            lot["viability"] = round(max(0.0, float(lot["viability"]) - days * 0.00035), 8)
            if lot["count"] <= 0 or lot["viability"] <= 0:
                continue
            traits = result["species_catalog"].get(lot["species_id"], SPECIES["meadow_grass"])
            suitability = _clamp(1.0 - abs(moisture - sum(traits["moisture"]) / 2.0) / 0.55) * _clamp(1.0 - site_shade * (1.0 - traits["shade_tolerance"]))
            drought_or_shade = suitability < 0.2
            if days >= 1.0 and (_stream(result["seed"], "germination", key, lot["seed_lot_id"], int(lot["age_days"])) < min(0.55, suitability * float(lot["viability"]) * 0.75)):
                lot["count"] -= 1
                plant_id = f"plant-{key.replace(',', '-')}-g{len(result['plants'])}"
                result["plants"].append(_plant_record(result["seed"], plant_id, lot["species_id"], x, y, len(result["plants"]), "seedling"))
                result["plant_ledgers"]["seed_transfers"].append({"kind": "germination", "seed_lot_id": lot["seed_lot_id"], "plant_id": plant_id, "count": 1, "suitability": round(suitability, 8)})
            elif days >= 1.0 and drought_or_shade and _stream(result["seed"], "germination-attempt", key, lot["seed_lot_id"], int(lot["age_days"])) < 0.35:
                lot["count"] -= 1
                result["plant_ledgers"]["seed_transfers"].append({"kind": "germination_failed", "seed_lot_id": lot["seed_lot_id"], "count": 1, "reason": "drought_or_shade", "suitability": round(suitability, 8)})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "plant_step", "revision": result["revision"]})
    return _finish(result)


def harvest_seeds(state: Mapping[str, Any], plant_id: str, count: int, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    if type(count) is not int or count <= 0:
        raise ValueError("count must be a positive integer")
    result = _copy_mutate(state, expected_revision, operation_id)
    plant = next((p for p in result["plants"] if p["plant_id"] == plant_id), None)
    if plant is None:
        raise KeyError(plant_id)
    take = min(count, int(plant["seed_supply"]))
    if take <= 0:
        raise ValueError("plant has no finite seeds available")
    plant["seed_supply"] -= take
    result["seed_inventory"].append({"seed_lot_id": f"harvest-{plant_id}-{result['revision']}", "species_id": plant["species_id"], "count": take, "viability": 0.92, "reserve_mass_kg": result["species_catalog"][plant["species_id"]]["seed_mass_kg"], "origin": plant_id})
    result["plant_ledgers"]["seed_transfers"].append({"kind": "harvest", "plant_id": plant_id, "count": take})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "harvest_seeds", "revision": result["revision"]})
    return _finish(result)


def plant_carried_seed(state: Mapping[str, Any], x: int, y: int, species_id: str, count: int = 1, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    if species_id not in SPECIES:
        raise KeyError(species_id)
    if type(count) is not int or count <= 0:
        raise ValueError("count must be a positive integer")
    result = _copy_mutate(state, expected_revision, operation_id)
    inventory = next((lot for lot in result["seed_inventory"] if lot["species_id"] == species_id and lot["count"] >= count), None)
    if inventory is None:
        raise ValueError("insufficient carried seed")
    inventory["count"] -= count
    key = _coord_key(x, y)
    if key not in result["seed_banks"]:
        raise KeyError((x, y))
    result["seed_banks"][key].append({"seed_lot_id": f"planted-{result['revision']}-{len(result['seed_banks'][key])}", "species_id": species_id, "count": count, "viability": inventory["viability"], "reserve_mass_kg": inventory["reserve_mass_kg"], "age_days": 0.0, "origin": "carried_inventory", "dormant": False})
    result["plant_ledgers"]["seed_transfers"].append({"kind": "planting", "species_id": species_id, "coord": {"x": x, "y": y}, "count": count})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "plant_carried_seed", "revision": result["revision"]})
    return _finish(result)


def cut_plant(state: Mapping[str, Any], plant_id: str, amount_kg: float | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    result = _copy_mutate(state, expected_revision, operation_id)
    plant = next((p for p in result["plants"] if p["plant_id"] == plant_id), None)
    if plant is None:
        raise KeyError(plant_id)
    traits = result["species_catalog"][plant["species_id"]]
    available = max(0.0, float(plant["biomass_kg"]) - float(plant["reserve_kg"]))
    amount = available if amount_kg is None else _finite(amount_kg, "amount_kg", 0.0, available)
    if amount <= 0:
        raise ValueError("plant has no harvestable biomass")
    plant["biomass_kg"] = round(float(plant["biomass_kg"]) - amount, 8)
    plant["stump"] = True
    plant["stage"] = "stump" if traits["coppice"] else "dead"
    plant["alive"] = bool(traits["coppice"] and float(plant["reserve_kg"]) > 0.0)
    result["underground"]["material_stocks"].setdefault("wood", {"initial_kg": 0.0, "available_kg": 0.0, "extracted_kg": 0.0, "loose_kg": 0.0, "spoil_kg": 0.0, "hauled_kg": 0.0, "deposited_kg": 0.0})
    result["underground"]["material_stocks"]["wood"]["loose_kg"] += amount
    result["underground"]["material_stocks"]["wood"]["extracted_kg"] += amount
    result["plant_ledgers"]["cuttings"].append({"plant_id": plant_id, "wood_kg": round(amount, 8), "remaining_reserve_kg": plant["reserve_kg"], "coppice": bool(traits["coppice"])})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "cut_plant", "revision": result["revision"]})
    return _finish(result)


def set_occupancy(state: Mapping[str, Any], node: str, occupant_id: str, occupied: bool = True, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    result = _copy_mutate(state, expected_revision, operation_id)
    if occupied:
        result["underground"]["occupancy"].setdefault(node, [])
        if occupant_id not in result["underground"]["occupancy"][node]:
            result["underground"]["occupancy"][node].append(occupant_id)
    else:
        result["underground"]["occupancy"].setdefault(node, [])
        result["underground"]["occupancy"][node] = [x for x in result["underground"]["occupancy"][node] if x != occupant_id]
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "occupancy", "revision": result["revision"]})
    return _finish(result)


def excavate(state: Mapping[str, Any], x: int, y: int, layer_id: str, volume_m3: float, actor_id: str | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    volume = _finite(volume_m3, "volume_m3", 0.0, 1e6)
    if volume <= 0:
        raise ValueError("volume_m3 must be positive")
    result = _copy_mutate(state, expected_revision, operation_id)
    key = _coord_key(x, y)
    cell = result["underground"]["cells"].get(key)
    if cell is None:
        raise KeyError((x, y))
    if result["underground"]["occupancy"].get(f"surface:{key}"):
        raise ValueError("cannot excavate occupied surface support")
    layer = next((layer for layer in cell["layers"] if layer["layer_id"] == layer_id), None)
    if layer is None or float(layer["remaining_volume_m3"]) + EPSILON < volume:
        raise ValueError("insufficient finite underground stock")
    if layer["occupied"]:
        raise ValueError("target layer is occupied")
    mass = _layer_mass(layer["material_id"], volume, {"materials": MATERIALS})
    layer["remaining_volume_m3"] = round(float(layer["remaining_volume_m3"]) - volume, 8)
    layer["exposed"] = True
    layer["support_required"] = True
    stock = result["underground"]["material_stocks"][layer["material_id"]]
    stock["available_kg"] = round(max(0.0, stock["available_kg"] - mass), 8)
    stock["extracted_kg"] = round(stock["extracted_kg"] + mass, 8)
    stock["loose_kg"] = round(stock["loose_kg"] + mass, 8)
    stock["spoil_kg"] = round(stock["spoil_kg"] + mass, 8)
    result["underground"]["spoil"][layer["material_id"]] = round(result["underground"]["spoil"].get(layer["material_id"], 0.0) + mass, 8)
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "excavate", "coord": {"x": x, "y": y}, "layer_id": layer_id, "actor_id": actor_id, "volume_m3": volume, "spoil_kg": mass, "revision": result["revision"]})
    return _finish(result)


def build_support(state: Mapping[str, Any], x: int, y: int, layer_id: str, material_id: str = "stone", amount_kg: float = 1.0, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    amount = _finite(amount_kg, "amount_kg", 0.0, 1e6)
    if amount <= 0 or material_id not in result_materials(state):
        raise ValueError("invalid support material or amount")
    result = _copy_mutate(state, expected_revision, operation_id)
    key = _coord_key(x, y)
    layer = next((layer for layer in result["underground"]["cells"].get(key, {}).get("layers", []) if layer["layer_id"] == layer_id), None)
    if layer is None:
        raise KeyError((x, y, layer_id))
    stock = result["underground"]["material_stocks"][material_id]
    if stock["loose_kg"] + EPSILON < amount:
        raise ValueError("support requires transported loose material")
    stock["loose_kg"] = round(stock["loose_kg"] - amount, 8)
    stock["deposited_kg"] = round(stock["deposited_kg"] + amount, 8)
    support_id = f"support-{result['revision']}-{len(result['underground']['supports']) + 1}"
    result["underground"]["supports"].append({"support_id": support_id, "coord": {"x": x, "y": y}, "layer_id": layer_id, "material_id": material_id, "amount_kg": amount, "intact": True})
    layer["support_required"] = False
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "build_support", "revision": result["revision"]})
    return _finish(result)


def result_materials(state: Mapping[str, Any]) -> set[str]:
    return set(state["underground"]["material_stocks"]) & set(MATERIALS)


def build_connector(state: Mapping[str, Any], from_node: str, to_node: str, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    def parse(node: str) -> tuple[int, int, str]:
        try:
            coord, layer = node.split("/", 1)
            x, y = (int(v) for v in coord.split(","))
            return x, y, layer
        except Exception as exc:
            raise ValueError("node must be x,y/layer") from exc
    fx, fy, fl = parse(from_node)
    tx, ty, tl = parse(to_node)
    if abs(fx - tx) + abs(fy - ty) > 1 or fl == tl and (fx, fy) == (tx, ty):
        raise ValueError("connectors only join adjacent cells or distinct layers")
    result = _copy_mutate(state, expected_revision, operation_id)
    for node, x, y, layer in ((from_node, fx, fy, fl), (to_node, tx, ty, tl)):
        cell = result["underground"]["cells"].get(_coord_key(x, y))
        if cell is None or not any(l["layer_id"] == layer and l["exposed"] for l in cell["layers"]):
            raise ValueError("both connector endpoints must be exposed by excavation")
    connector_id = f"connector-{result['revision']}-{len(result['underground']['connectors']) + 1}"
    result["underground"]["connectors"].append({"connector_id": connector_id, "from": from_node, "to": to_node, "open": True})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "build_connector", "revision": result["revision"]})
    return _finish(result)


def _connected(connectors: list[Mapping[str, Any]], start: str, goal: str) -> bool:
    seen = {start}
    changed = True
    while changed:
        changed = False
        for connector in connectors:
            if not connector.get("open"):
                continue
            a, b = connector["from"], connector["to"]
            if a in seen and b not in seen:
                seen.add(b); changed = True
            if b in seen and a not in seen:
                seen.add(a); changed = True
    return goal in seen


def move_underground(state: Mapping[str, Any], actor_id: str, from_node: str, to_node: str, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    result = _copy_mutate(state, expected_revision, operation_id)
    if not _connected(result["underground"]["connectors"], from_node, to_node):
        raise ValueError("no connected underground route; teleportation is forbidden")
    result["underground"]["occupancy"].setdefault(from_node, [])
    result["underground"]["occupancy"].setdefault(to_node, [])
    result["underground"]["occupancy"][from_node] = [x for x in result["underground"]["occupancy"][from_node] if x != actor_id]
    result["underground"]["occupancy"][to_node].append(actor_id)
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "move_underground", "actor_id": actor_id, "from": from_node, "to": to_node, "revision": result["revision"]})
    return _finish(result)


def haul_spoil(state: Mapping[str, Any], material_id: str, amount_kg: float, from_node: str, to_node: str, actor_id: str | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    if _already_applied(state, operation_id):
        return copy.deepcopy(dict(state))
    amount = _finite(amount_kg, "amount_kg", 0.0, 1e9)
    if amount <= 0 or material_id not in state["underground"]["spoil"]:
        raise ValueError("invalid finite spoil amount")
    result = _copy_mutate(state, expected_revision, operation_id)
    spoil = float(result["underground"]["spoil"].get(material_id, 0.0))
    if spoil + EPSILON < amount:
        raise ValueError("insufficient loose spoil")
    if from_node != to_node and not _connected(result["underground"]["connectors"], from_node, to_node):
        raise ValueError("haul route is not connected")
    result["underground"]["spoil"][material_id] = round(spoil - amount, 8)
    stock = result["underground"]["material_stocks"][material_id]
    stock["loose_kg"] = round(max(0.0, stock["loose_kg"] - amount), 8)
    stock["hauled_kg"] = round(stock["hauled_kg"] + amount, 8)
    result["underground"]["hauls"].append({"material_id": material_id, "amount_kg": amount, "from": from_node, "to": to_node, "actor_id": actor_id})
    result["underground"]["operations"].append({"operation_id": operation_id, "kind": "haul_spoil", "revision": result["revision"]})
    return _finish(result)


def validate_state(state: Mapping[str, Any]) -> bool:
    if not isinstance(state, Mapping) or state.get("contract_version") != CONTRACT_VERSION or state.get("g47_version") != G47_VERSION:
        raise ValueError("unsupported G4-G7 sidecar contract")
    if not isinstance(state.get("revision"), int) or state["revision"] < 0:
        raise ValueError("invalid sidecar revision")
    if set(state.get("species_catalog", {})) != set(SPECIES):
        raise ValueError("species catalog mismatch")
    for plant in state.get("plants", []):
        if plant["species_id"] not in SPECIES or float(plant["biomass_kg"]) < -EPSILON or float(plant["reserve_kg"]) < -EPSILON or int(plant["seed_supply"]) < 0:
            raise ValueError("invalid finite plant state")
    for key, lots in state.get("seed_banks", {}).items():
        if len(key.split(",")) != 2:
            raise ValueError("invalid seed-bank coordinate")
        for lot in lots:
            if lot["species_id"] not in SPECIES or int(lot["count"]) < 0 or not 0.0 <= float(lot["viability"]) <= 1.0:
                raise ValueError("invalid seed lot")
    underground = state.get("underground", {})
    for material, stock in underground.get("material_stocks", {}).items():
        for name in ("initial_kg", "available_kg", "extracted_kg", "loose_kg", "spoil_kg", "hauled_kg", "deposited_kg"):
            _finite(stock.get(name, 0.0), f"stock {material}.{name}")
    for cell in underground.get("cells", {}).values():
        for layer in cell.get("layers", []):
            if float(layer["remaining_volume_m3"]) < -EPSILON or float(layer["remaining_volume_m3"]) > float(layer["initial_volume_m3"]) + EPSILON:
                raise ValueError("underground stock increased")
    if state.get("state_hash") and state["state_hash"] != state_hash(state):
        raise ValueError("sidecar checksum mismatch")
    return True


def inspect(state: Mapping[str, Any]) -> dict[str, Any]:
    validate_state(state)
    return {"contract_version": state["contract_version"], "world_id": state["world_id"], "revision": state["revision"], "state_hash": state_hash(state), "plant_count": len(state["plants"]), "alive_plant_count": sum(bool(p["alive"]) for p in state["plants"]), "seed_bank_count": sum(int(lot["count"]) for lots in state["seed_banks"].values() for lot in lots), "connector_count": len(state["underground"]["connectors"]), "support_count": len(state["underground"]["supports"]), "operation_count": len(state["underground"]["operations"])}


def save(state: Mapping[str, Any], path: str | os.PathLike[str]) -> dict[str, Any]:
    validate_state(state)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(state), sort_keys=True, indent=2, allow_nan=False))
    return {"path": str(target), "state_hash": state_hash(state)}


def resume(path: str | os.PathLike[str]) -> dict[str, Any]:
    state = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_state(state)
    return state


def replay(state_or_path: Mapping[str, Any] | str | os.PathLike[str], operations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    state = resume(state_or_path) if isinstance(state_or_path, (str, os.PathLike)) else copy.deepcopy(dict(state_or_path))
    dispatch = {"plant_step": plant_step, "harvest_seeds": harvest_seeds, "plant_carried_seed": plant_carried_seed, "cut_plant": cut_plant, "set_occupancy": set_occupancy, "excavate": excavate, "build_support": build_support, "build_connector": build_connector, "move_underground": move_underground, "haul_spoil": haul_spoil}
    for operation in operations:
        args = dict(operation)
        kind = args.pop("kind", None)
        if kind not in dispatch:
            raise ValueError(f"unknown replay operation: {kind}")
        state = dispatch[kind](state, **args)
    return state


# Small vocabulary aliases make the sidecar convenient for headless experiments
# without adding another integration surface.
create = initialize
advance = plant_step
collect_seeds = harvest_seeds
plant_seed = plant_carried_seed
extract_underground = excavate
connect = build_connector
support = build_support
haul = haul_spoil


__all__ = ["CONTRACT_VERSION", "G47_VERSION", "SPECIES", "ConflictError", "species_catalog", "initialize", "create", "validate_state", "state_hash", "plant_step", "advance", "harvest_seeds", "collect_seeds", "plant_carried_seed", "plant_seed", "cut_plant", "set_occupancy", "excavate", "extract_underground", "build_support", "support", "build_connector", "connect", "move_underground", "haul_spoil", "haul", "inspect", "save", "resume", "replay"]
