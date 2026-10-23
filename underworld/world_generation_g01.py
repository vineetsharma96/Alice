"""Bounded, additive G0-G3 world-generation research slice.

This module is deliberately independent of the native world and storage layers.  It
owns no actors, movement, weather scheduler, or existing save files; callers may
copy the JSON manifest into a separate experiment.  All mutations are pure
copy-on-write transforms so a stale caller cannot silently refill or overwrite a
world.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CONTRACT_VERSION = "alice.world.g01/v1"
GENERATOR_VERSION = "g01.2"
MAX_CELLS = 4096
EPSILON = 1e-9


class ConflictError(ValueError):
    """Raised when a copy-on-write operation was based on an old revision."""


PRESETS: dict[str, dict[str, Any]] = {
    "temperate_woodland_meadow": {
        "moisture": 0.58,
        "rainfall_mm": 5.0,
        "vegetation_density": 0.72,
        "parent_materials": ("weathered_rock", "stone", "gravel"),
        "water_table": 0.34,
    },
    "dry_scrub_rocky": {
        "moisture": 0.24,
        "rainfall_mm": 1.6,
        "vegetation_density": 0.34,
        "parent_materials": ("stone", "gravel", "weathered_rock"),
        "water_table": 0.12,
    },
    "wet_riparian": {
        "moisture": 0.80,
        "rainfall_mm": 8.0,
        "vegetation_density": 0.84,
        "parent_materials": ("gravel", "weathered_rock", "stone"),
        "water_table": 0.62,
    },
}


MATERIALS: dict[str, dict[str, Any]] = {
    "sand": {"hardness": 1.0, "density_kg_m3": 1600.0, "unit": "kg", "construction": "fill"},
    "silt": {"hardness": 0.7, "density_kg_m3": 1350.0, "unit": "kg", "construction": "soil"},
    "clay": {"hardness": 1.5, "density_kg_m3": 1450.0, "unit": "kg", "construction": "soil"},
    "gravel": {"hardness": 4.0, "density_kg_m3": 1900.0, "unit": "kg", "construction": "aggregate"},
    "stone": {"hardness": 7.0, "density_kg_m3": 2600.0, "unit": "kg", "construction": "stone"},
    "weathered_rock": {"hardness": 5.0, "density_kg_m3": 2200.0, "unit": "kg", "construction": "rock"},
    "organic_litter": {"hardness": 0.2, "density_kg_m3": 400.0, "unit": "kg", "construction": "organic"},
    "iron_ore": {"hardness": 6.0, "density_kg_m3": 3200.0, "unit": "kg", "construction": "ore"},
    "copper_ore": {"hardness": 5.5, "density_kg_m3": 3000.0, "unit": "kg", "construction": "ore"},
}


def preset_config(name: str = "temperate_woodland_meadow", **overrides: Any) -> dict[str, Any]:
    """Return a small bounded configuration suitable for headless experiments."""
    if name not in PRESETS:
        raise ValueError(f"unknown climate preset: {name}")
    result: dict[str, Any] = {
        "width": 12,
        "height": 12,
        "cell_scale_m": 1.0,
        "layer_depth_m": 3.0,
        "climate_preset": name,
        "geological_preset": "simple_continuous",
        "relief": 1.0,
        "water_availability": 1.0,
        "vegetation_density": PRESETS[name]["vegetation_density"],
        "diversity": 0.6,
        "starting_population": 0,
        "mode": "research",
    }
    result.update(overrides)
    return result


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    value = float(value)
    if value < low or value > high:
        raise ValueError(f"{label} must be in [{low}, {high}]")
    return value


def validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(config, Mapping):
        raise ValueError("config must be a mapping")
    merged = preset_config(str(config.get("climate_preset", "temperate_woodland_meadow")))
    merged.update(dict(config))
    width = merged.get("width")
    height = merged.get("height")
    if type(width) is not int or type(height) is not int or not 4 <= width <= 64 or not 4 <= height <= 64:
        raise ValueError("width and height must be integers in [4, 64]")
    if width * height > MAX_CELLS:
        raise ValueError("cell budget exceeds bounded G01 limit")
    _number(merged["cell_scale_m"], "cell_scale_m", 0.25, 10.0)
    _number(merged["layer_depth_m"], "layer_depth_m", 0.5, 20.0)
    _number(merged["relief"], "relief", 0.0, 2.0)
    _number(merged["water_availability"], "water_availability", 0.0, 1.0)
    _number(merged["vegetation_density"], "vegetation_density", 0.0, 1.0)
    _number(merged["diversity"], "diversity", 0.0, 1.0)
    if type(merged.get("starting_population")) is not int or not 0 <= merged["starting_population"] <= 64:
        raise ValueError("starting_population must be an integer in [0, 64]")
    if merged["climate_preset"] not in PRESETS:
        raise ValueError(f"unknown climate preset: {merged['climate_preset']}")
    if merged.get("geological_preset") != "simple_continuous":
        raise ValueError("only the versioned simple_continuous geology is supported")
    if merged.get("mode") not in {"research", "guided"}:
        raise ValueError("mode must be research or guided")
    return merged


def _u(seed: int, domain: str, x: int, y: int, salt: int = 0) -> float:
    payload = f"{int(seed)}|{domain}|{int(x)}|{int(y)}|{int(salt)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") / 2**64


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def manifest_hash(manifest: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(manifest))
    body.pop("manifest_hash", None)
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _texture(seed: int, x: int, y: int, horizon: str) -> dict[str, float]:
    raw = [_u(seed, f"texture:{horizon}", x, y, i) + 0.05 for i in range(3)]
    total = sum(raw)
    return {k: raw[i] / total for i, k in enumerate(("sand", "silt", "clay"))}


def _elevation(seed: int, x: int, y: int, relief: float) -> float:
    broad = 0.5 + 0.24 * math.sin((x + seed % 17) / 5.2) + 0.18 * math.cos((y - seed % 11) / 4.4)
    local = 0.16 * (_u(seed, "relief", x, y) - 0.5)
    return _clamp(0.5 + relief * (broad - 0.5 + local))


def _material_mass(material: str, volume_m3: float) -> float:
    return volume_m3 * MATERIALS[material]["density_kg_m3"]


def _base_horizons(seed: int, x: int, y: int, cfg: Mapping[str, Any], parent: str, moisture: float) -> list[dict[str, Any]]:
    depth = float(cfg["layer_depth_m"])
    preset = PRESETS[cfg["climate_preset"]]
    organic = min(depth * 0.12, 0.05 + 0.16 * preset["vegetation_density"] * (0.7 + 0.6 * _u(seed, "organic", x, y)))
    topsoil = min(depth * 0.28, 0.18 + 0.28 * (0.4 + moisture))
    subsoil = min(depth * 0.25, 0.22 + 0.18 * (1.0 - moisture))
    weathered = min(depth * 0.30, 0.42 + 0.16 * _u(seed, "weathered", x, y))
    bedrock = max(0.0, depth - organic - topsoil - subsoil - weathered)
    specs = [
        ("O", "organic_litter", organic, 0.35),
        ("A", "silt", topsoil, 0.42),
        ("B", "clay", subsoil, 0.32),
        ("C", parent, weathered, 0.18),
        ("R", "stone", bedrock, 0.04),
    ]
    horizons: list[dict[str, Any]] = []
    area = float(cfg["cell_scale_m"]) ** 2
    for layer_id, material, thickness, organic_fraction in specs:
        texture = _texture(seed, x, y, layer_id)
        porosity = _clamp(0.2 + 0.35 * (texture["silt"] + texture["clay"]) + organic_fraction * 0.25, 0.05, 0.65)
        volume = max(0.0, thickness * area)
        capacity = volume * porosity
        water = capacity * _clamp(moisture * (0.5 + 0.4 * _u(seed, f"water:{layer_id}", x, y)))
        horizons.append({
            "layer_id": layer_id,
            "material_id": material,
            "thickness_m": round(thickness, 8),
            "volume_m3": round(volume, 8),
            "bulk_density_kg_m3": MATERIALS[material]["density_kg_m3"],
            "porosity": round(porosity, 8),
            "water_m3": round(water, 8),
            "water_capacity_m3": round(capacity, 8),
            "texture": {k: round(v, 8) for k, v in texture.items()},
            "organic_matter_kg": round(_material_mass("organic_litter", volume) * organic_fraction, 8),
            "nutrients_available": {k: round(volume * (0.3 + moisture) * f, 8) for k, f in (("N", 0.7), ("P", 0.25), ("K", 0.5))},
            "nutrients_bound": {k: round(volume * (1.0 - moisture) * f, 8) for k, f in (("N", 0.8), ("P", 0.4), ("K", 0.6))},
            "compaction": round(_clamp(0.2 + 0.35 * (1.0 - organic_fraction) + 0.1 * _u(seed, "compaction", x, y), 0.0, 1.0), 8),
        })
    return horizons


def _new_cell(seed: int, x: int, y: int, cfg: Mapping[str, Any]) -> dict[str, Any]:
    preset = PRESETS[cfg["climate_preset"]]
    elevation = _elevation(seed, x, y, float(cfg["relief"]))
    base = preset["moisture"] * float(cfg["water_availability"])
    moisture = _clamp(base + 0.23 * (1.0 - elevation) + 0.16 * (_u(seed, "moisture", x, y) - 0.5))
    parent = preset["parent_materials"][int(_u(seed, "parent", x, y) * len(preset["parent_materials"])) % len(preset["parent_materials"])]
    threshold = 0.18 + 0.12 * preset["water_table"]
    standing = _clamp((threshold - elevation) * 0.8) * float(cfg["water_availability"]) * float(cfg["cell_scale_m"]) ** 2
    horizons = _base_horizons(seed, x, y, cfg, parent, moisture)
    seed_count = int(round(float(cfg["vegetation_density"]) * (0.4 + _u(seed, "seed-bank", x, y)) * 8))
    species = ("woodland_tree", "meadow_grass", "riparian_reed", "dry_scrub")
    seeds = []
    if seed_count:
        for i in range(seed_count):
            species_id = species[int(_u(seed, "species", x, y, i) * len(species)) % len(species)]
            seeds.append({
                "seed_lot_id": f"seed-{x}-{y}-{i}",
                "species_id": species_id,
                "viability": round(_clamp(0.55 + 0.35 * _u(seed, "viability", x, y, i)), 8),
                "reserve_mass_kg": round(0.001 + 0.009 * _u(seed, "seed-mass", x, y, i), 8),
            })
    return {
        "coord": {"x": x, "y": y},
        "elevation": round(elevation, 8),
        "slope": 0.0,
        "moisture": round(moisture, 8),
        "parent_material": parent,
        "surface_water_m3": round(standing, 8),
        "standing_water": bool(standing > 0.001),
        "exposed_layer_id": "O",
        "horizons": horizons,
        "plant_seeds": seeds,
        "plant_condition": {"water_factor": round(_clamp(moisture * 1.2), 8), "drought": False, "waterlogged": False},
    }


def _check_revision(manifest: Mapping[str, Any], expected_revision: int | None) -> None:
    if expected_revision is not None and manifest.get("revision") != expected_revision:
        raise ConflictError("manifest revision is stale")


def generate(seed: int, config: Mapping[str, Any] | None = None, *, cell_order=None) -> dict[str, Any]:
    """Generate one complete bounded manifest using coordinate-stable streams."""
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    cfg = validate_config(config or preset_config())
    coordinates=[(x,y) for y in range(cfg['height']) for x in range(cfg['width'])]
    order=coordinates if cell_order is None else list(cell_order)
    if len(order)!=len(coordinates) or set(order)!=set(coordinates):
        raise ValueError('Generation order must contain every cell exactly once')
    cells = [_new_cell(seed, x, y, cfg) for x,y in order]
    cells.sort(key=lambda cell:(cell['coord']['y'],cell['coord']['x']))
    by_coord = {(c["coord"]["x"], c["coord"]["y"]): c for c in cells}
    for cell in cells:
        x, y = cell["coord"]["x"], cell["coord"]["y"]
        neighbors = [by_coord[(nx, ny)]["elevation"] for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if (nx, ny) in by_coord]
        cell["slope"] = round(max((abs(cell["elevation"] - n) for n in neighbors), default=0.0), 8)
    deposits = []
    for cell in cells:
        x, y = cell["coord"]["x"], cell["coord"]["y"]
        chance = 0.035 + 0.04 * float(cfg["diversity"])
        if _u(seed, "deposit", x, y) < chance:
            ore = "iron_ore" if _u(seed, "deposit-kind", x, y) < 0.58 else "copper_ore"
            stock = round(8.0 + 42.0 * _u(seed, "deposit-stock", x, y), 8)
            grade = round(0.25 + 0.45 * _u(seed, "deposit-grade", x, y), 8)
            gangue = round(stock * (1.0 - grade) / grade, 8)
            deposits.append({
                "deposit_id": f"deposit-{x}-{y}",
                "coord": {"x": x, "y": y},
                "material_id": ore,
                "host_material": cell["parent_material"],
                "grade": grade,
                "initial_ore_kg": stock,
                "remaining_ore_kg": stock,
                "initial_gangue_kg": gangue,
                "remaining_gangue_kg": gangue,
                "exposed": False,
            })
    stocks: dict[str, dict[str, float]] = {}
    for material in MATERIALS:
        horizon_mass = sum(_material_mass(h["material_id"], h["volume_m3"]) for c in cells for h in c["horizons"] if h["material_id"] == material)
        deposit_mass = sum((d["initial_ore_kg"] if d["material_id"] == material else 0.0) + (d["initial_gangue_kg"] if d["host_material"] == material else 0.0) for d in deposits)
        stocks[material] = {"initial_kg": round(horizon_mass + deposit_mass, 8), "available_kg": round(horizon_mass + deposit_mass, 8), "loose_kg": 0.0, "extracted_kg": 0.0, "spoil_kg": 0.0, "deposited_kg": 0.0}
    manifest: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "revision": 0,
        "world_id": "world-" + hashlib.sha256(f"{seed}|{_canonical(cfg)}|{GENERATOR_VERSION}".encode()).hexdigest()[:20],
        "config": cfg,
        "dimensions": {"width": cfg["width"], "height": cfg["height"], "cell_scale_m": cfg["cell_scale_m"]},
        "materials": copy.deepcopy(MATERIALS),
        "cells": cells,
        "deposits": deposits,
        "stocks": stocks,
        "ledgers": {"water": [], "material_transfers": [], "operations": []},
        "diagnostics": {
            "cell_count": len(cells),
            "deposit_count": len(deposits),
            "limits": {"max_cells": MAX_CELLS, "max_layer_depth_m": 20.0},
            "abstractions": ["coordinate-hash streams", "heuristic soil horizons", "bounded shallow water", "no geological formation simulation"],
        },
    }
    validate_manifest(manifest)
    manifest["manifest_hash"] = manifest_hash(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> bool:
    if not isinstance(manifest, Mapping) or manifest.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("unsupported world manifest contract")
    if manifest.get("generator_version") != GENERATOR_VERSION:
        raise ValueError("unsupported generator version")
    cfg = validate_config(manifest.get("config", {}))
    if manifest.get("revision", -1) < 0 or len(manifest.get("cells", [])) != cfg["width"] * cfg["height"]:
        raise ValueError("invalid cell count or revision")
    seen = set()
    for cell in manifest["cells"]:
        coord = (cell["coord"]["x"], cell["coord"]["y"])
        if coord in seen or not (0 <= coord[0] < cfg["width"] and 0 <= coord[1] < cfg["height"]):
            raise ValueError("invalid or duplicate cell coordinate")
        seen.add(coord)
        for bounded in ("elevation", "slope", "moisture"):
            _number(cell[bounded], f"cell {bounded}", 0.0, 1.0)
        total_depth = 0.0
        for horizon in cell["horizons"]:
            _number(horizon["thickness_m"], "horizon thickness", 0.0, cfg["layer_depth_m"])
            _number(horizon["porosity"], "horizon porosity", 0.0, 1.0)
            _number(horizon["water_m3"], "horizon water", 0.0, horizon["water_capacity_m3"] + EPSILON)
            texture = horizon["texture"]
            if any(float(texture.get(k, -1)) < -EPSILON for k in ("sand", "silt", "clay")) or abs(sum(texture.values()) - 1.0) > 1e-6:
                raise ValueError("invalid texture fractions")
            total_depth += horizon["thickness_m"]
        if total_depth > cfg["layer_depth_m"] + 1e-6 or cell["surface_water_m3"] < -EPSILON:
            raise ValueError("invalid horizon depth or surface water")
    for deposit in manifest.get("deposits", []):
        for key in ("initial_ore_kg", "remaining_ore_kg", "initial_gangue_kg", "remaining_gangue_kg"):
            _number(deposit[key], key, 0.0, float("inf"))
        if deposit["remaining_ore_kg"] > deposit["initial_ore_kg"] + EPSILON or deposit["remaining_gangue_kg"] > deposit["initial_gangue_kg"] + EPSILON:
            raise ValueError("deposit stock increased")
    for material, stock in manifest.get("stocks", {}).items():
        if material not in MATERIALS:
            raise ValueError("unknown material stock")
        for key in ("initial_kg", "available_kg", "loose_kg", "extracted_kg", "spoil_kg", "deposited_kg"):
            _number(stock[key], f"stock {material}.{key}", 0.0, float("inf"))
    if "ledgers" not in manifest or not isinstance(manifest["ledgers"], Mapping):
        raise ValueError("missing ledgers")
    if manifest.get("manifest_hash") and manifest["manifest_hash"] != manifest_hash(manifest):
        raise ValueError("manifest checksum mismatch")
    return True


def generate_order_invariant(seed: int, config: Mapping[str, Any] | None = None, orders: Sequence[Sequence[tuple[int, int]]] | None = None) -> bool:
    """Check same-seed output under ordinary, reversed, and shuffled request order."""
    cfg = validate_config(config or preset_config())
    first = generate(seed, cfg)
    second = generate(seed, cfg)
    if manifest_hash(first) != manifest_hash(second):
        return False
    if orders is not None:
        for order in orders:
            if manifest_hash(generate(seed,cfg,cell_order=order))!=manifest_hash(first):return False
    return True


def _mutate(manifest: Mapping[str, Any], expected_revision: int | None) -> dict[str, Any]:
    validate_manifest(manifest)
    _check_revision(manifest, expected_revision)
    result = copy.deepcopy(dict(manifest))
    result["revision"] += 1
    result.pop("manifest_hash", None)
    return result


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(result)
    result["manifest_hash"] = manifest_hash(result)
    return result


def extract(manifest: Mapping[str, Any], deposit_id: str, amount_kg: float, actor_id: str | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    """Extract finite ore and its proportional gangue; repeated extraction cannot refill stock."""
    amount = _number(amount_kg, "amount_kg", 0.0, 1e9)
    if amount <= 0:
        raise ValueError("amount_kg must be positive")
    if operation_id and any(op.get("operation_id") == operation_id for op in manifest["ledgers"]["operations"]):
        return copy.deepcopy(dict(manifest))
    result = _mutate(manifest, expected_revision)
    deposit = next((d for d in result["deposits"] if d["deposit_id"] == deposit_id), None)
    if deposit is None:
        raise KeyError(deposit_id)
    ore = min(amount, deposit["remaining_ore_kg"])
    gangue_need = ore * (1.0 - deposit["grade"]) / deposit["grade"]
    gangue = min(gangue_need, deposit["remaining_gangue_kg"])
    if gangue + EPSILON < gangue_need:
        ore = gangue * deposit["grade"] / (1.0 - deposit["grade"])
        gangue = min(gangue, gangue_need)
    deposit["remaining_ore_kg"] = round(deposit["remaining_ore_kg"] - ore, 8)
    deposit["remaining_gangue_kg"] = round(deposit["remaining_gangue_kg"] - gangue, 8)
    ore_stock = result["stocks"][deposit["material_id"]]
    host_stock = result["stocks"][deposit["host_material"]]
    ore_stock["available_kg"] = round(max(0.0, ore_stock["available_kg"] - ore), 8)
    ore_stock["loose_kg"] = round(ore_stock["loose_kg"] + ore, 8)
    ore_stock["extracted_kg"] = round(ore_stock["extracted_kg"] + ore, 8)
    host_stock["available_kg"] = round(max(0.0, host_stock["available_kg"] - gangue), 8)
    host_stock["loose_kg"] = round(host_stock["loose_kg"] + gangue, 8)
    host_stock["spoil_kg"] = round(host_stock["spoil_kg"] + gangue, 8)
    result["ledgers"]["material_transfers"].append({"kind": "extraction", "deposit_id": deposit_id, "actor_id": actor_id, "ore_kg": round(ore, 8), "gangue_kg": round(gangue, 8), "requested_kg": amount})
    result["ledgers"]["operations"].append({"operation_id": operation_id, "kind": "extract", "revision": result["revision"]})
    return _finish(result)


def excavate(manifest: Mapping[str, Any], x: int, y: int, layer_id: str, volume_m3: float, actor_id: str | None = None, expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    """Remove an existing horizon volume and account the resulting spoil."""
    volume = _number(volume_m3, "volume_m3", 0.0, 1e9)
    if volume <= 0:
        raise ValueError("volume_m3 must be positive")
    result = _mutate(manifest, expected_revision)
    cell = next((c for c in result["cells"] if c["coord"] == {"x": x, "y": y}), None)
    if cell is None:
        raise KeyError((x, y))
    horizon = next((h for h in cell["horizons"] if h["layer_id"] == layer_id), None)
    if horizon is None or horizon["volume_m3"] + EPSILON < volume:
        raise ValueError("insufficient exposed horizon stock")
    mass = _material_mass(horizon["material_id"], volume)
    horizon["volume_m3"] = round(horizon["volume_m3"] - volume, 8)
    horizon["thickness_m"] = round(horizon["volume_m3"] / (float(result["config"]["cell_scale_m"]) ** 2), 8)
    if horizon["water_capacity_m3"]:
        ratio = horizon["volume_m3"] / (horizon["water_capacity_m3"] / horizon["porosity"] or 1.0)
        horizon["water_capacity_m3"] = round(horizon["volume_m3"] * horizon["porosity"], 8)
        horizon["water_m3"] = round(min(horizon["water_m3"] * ratio, horizon["water_capacity_m3"]), 8)
    if horizon["volume_m3"] <= EPSILON:
        cell["horizons"].remove(horizon)
    cell["exposed_layer_id"] = cell["horizons"][0]["layer_id"] if cell["horizons"] else "void"
    stock = result["stocks"][horizon["material_id"]]
    stock["available_kg"] = round(max(0.0, stock["available_kg"] - mass), 8)
    stock["loose_kg"] = round(stock["loose_kg"] + mass, 8)
    stock["spoil_kg"] = round(stock["spoil_kg"] + mass, 8)
    result["ledgers"]["material_transfers"].append({"kind": "excavation", "coord": {"x": x, "y": y}, "layer_id": layer_id, "actor_id": actor_id, "spoil_material": horizon["material_id"], "spoil_kg": round(mass, 8)})
    result["ledgers"]["operations"].append({"operation_id": operation_id, "kind": "excavate", "revision": result["revision"]})
    return _finish(result)


def deposit(manifest: Mapping[str, Any], x: int, y: int, material_id: str, amount_kg: float, source: str = "spoil", expected_revision: int | None = None, operation_id: str | None = None) -> dict[str, Any]:
    """Place carried loose stock as explicit backfill; it never recreates topsoil."""
    if material_id not in MATERIALS:
        raise KeyError(material_id)
    amount = _number(amount_kg, "amount_kg", 0.0, 1e9)
    result = _mutate(manifest, expected_revision)
    cell = next((c for c in result["cells"] if c["coord"] == {"x": x, "y": y}), None)
    if cell is None:
        raise KeyError((x, y))
    stock = result["stocks"][material_id]
    if stock["loose_kg"] + EPSILON < amount:
        raise ValueError("insufficient loose stock")
    stock["loose_kg"] = round(stock["loose_kg"] - amount, 8)
    stock["deposited_kg"] = round(stock["deposited_kg"] + amount, 8)
    volume = amount / MATERIALS[material_id]["density_kg_m3"]
    layer_id = f"backfill-{result['revision']}"
    cell["horizons"].insert(0, {"layer_id": layer_id, "material_id": material_id, "thickness_m": round(volume / (float(result["config"]["cell_scale_m"]) ** 2), 8), "volume_m3": round(volume, 8), "bulk_density_kg_m3": MATERIALS[material_id]["density_kg_m3"], "porosity": 0.25, "water_m3": 0.0, "water_capacity_m3": round(volume * 0.25, 8), "texture": {"sand": 0.7, "silt": 0.2, "clay": 0.1}, "organic_matter_kg": 0.0, "nutrients_available": {"N": 0.0, "P": 0.0, "K": 0.0}, "nutrients_bound": {"N": 0.0, "P": 0.0, "K": 0.0}, "compaction": 0.8})
    cell["exposed_layer_id"] = layer_id
    result["ledgers"]["material_transfers"].append({"kind": "deposit", "coord": {"x": x, "y": y}, "material_id": material_id, "source": source, "amount_kg": amount})
    result["ledgers"]["operations"].append({"operation_id": operation_id, "kind": "deposit", "revision": result["revision"]})
    return _finish(result)


def soil_step(manifest: Mapping[str, Any], rainfall_mm: float = 0.0, temperature_c: float = 15.0, daylight_fraction: float = 0.5, dt_days: float = 1.0, expected_revision: int | None = None) -> dict[str, Any]:
    """Advance bounded soil water using positivity-preserving local transfers."""
    rain = _number(rainfall_mm, "rainfall_mm", 0.0, 1000.0)
    temp = _number(temperature_c, "temperature_c", -80.0, 80.0)
    daylight = _number(daylight_fraction, "daylight_fraction", 0.0, 1.0)
    dt = _number(dt_days, "dt_days", 0.0, 365.0)
    result = _mutate(manifest, expected_revision)
    total = {k: 0.0 for k in ("rainfall_in", "infiltration", "percolation", "evaporation", "plant_uptake", "runoff", "initial_storage", "final_storage")}
    area = float(result["config"]["cell_scale_m"]) ** 2
    for cell in result["cells"]:
        horizons = cell["horizons"]
        initial = cell["surface_water_m3"] + sum(h["water_m3"] for h in horizons)
        incoming = rain / 1000.0 * area
        top = horizons[0] if horizons else None
        # Rain enters the surface horizon first; deeper capacity is reached by
        # explicit percolation below.  This prevents silently dropping water when
        # the top horizon fills while preserving a closed inlet/outlet ledger.
        capacity = max(0.0, (top["water_capacity_m3"] - top["water_m3"]) if top else 0.0)
        texture_clay = top["texture"]["clay"] if top else 0.0
        organic = top["organic_matter_kg"] if top else 0.0
        compaction = top["compaction"] if top else 1.0
        infiltration_capacity = capacity * _clamp(0.45 + 0.5 * (1.0 - compaction) + 0.15 * texture_clay + 0.05 * min(1.0, organic), 0.05, 1.0)
        infiltrated = min(incoming + cell["surface_water_m3"], infiltration_capacity)
        cell["surface_water_m3"] = max(0.0, incoming + cell["surface_water_m3"] - infiltrated)
        if top:
            top["water_m3"] = min(top["water_capacity_m3"], top["water_m3"] + infiltrated)
        percolated = 0.0
        for index in range(len(horizons) - 1):
            upper, lower = horizons[index], horizons[index + 1]
            transfer = min(upper["water_m3"] * 0.12 * dt * (1.0 - upper["compaction"]), max(0.0, lower["water_capacity_m3"] - lower["water_m3"]))
            upper["water_m3"] -= transfer
            lower["water_m3"] += transfer
            percolated += transfer
        evap_rate = max(0.0, (0.0015 + max(0.0, temp) * 0.00008) * daylight * dt * (1.0 - 0.35 * min(1.0, organic)))
        evaporation = min(sum(h["water_m3"] for h in horizons), evap_rate)
        if evaporation and horizons:
            remaining = evaporation
            for h in horizons:
                take = min(h["water_m3"], remaining)
                h["water_m3"] -= take
                remaining -= take
                if remaining <= EPSILON:
                    break
        uptake = min(sum(h["water_m3"] for h in horizons), 0.0007 * len(cell["plant_seeds"]) * dt)
        if uptake and horizons:
            take = min(horizons[0]["water_m3"], uptake)
            horizons[0]["water_m3"] -= take
            uptake = take
        storage = cell["surface_water_m3"] + sum(h["water_m3"] for h in horizons)
        runoff = max(0.0, cell["surface_water_m3"])
        cell["surface_water_m3"] = 0.0
        total["rainfall_in"] += incoming
        total["infiltration"] += infiltrated
        total["percolation"] += percolated
        total["evaporation"] += evaporation
        total["plant_uptake"] += uptake
        total["runoff"] += runoff
        total["initial_storage"] += initial
        total["final_storage"] += storage - runoff
        capacity_total = sum(h["water_capacity_m3"] for h in horizons)
        ratio = (sum(h["water_m3"] for h in horizons) / capacity_total) if capacity_total else 0.0
        # This is a declared bounded plant stress classification, not a claim
        # that every pore is saturated; sustained storage above ~68% is the
        # waterlogging regime for this research abstraction.
        cell["plant_condition"] = {"water_factor": round(_clamp(ratio * 1.35), 8), "drought": ratio < 0.12, "waterlogged": ratio > 0.68}
        cell["moisture"] = round(_clamp(0.7 * cell["moisture"] + 0.3 * _clamp(ratio)), 8)
        cell["standing_water"] = False
    total["balance_error"] = round(total["initial_storage"] + total["rainfall_in"] - total["evaporation"] - total["plant_uptake"] - total["runoff"] - total["final_storage"], 10)
    if abs(total["balance_error"]) > 1e-6:
        raise ValueError(f"soil water ledger did not close: {total['balance_error']}")
    result["ledgers"]["water"].append({"rainfall_mm": rain, "temperature_c": temp, "daylight_fraction": daylight, "dt_days": dt, **{k: round(v, 10) for k, v in total.items()}})
    return _finish(result)


def inspect(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    return {
        "contract_version": manifest["contract_version"],
        "world_id": manifest["world_id"],
        "revision": manifest["revision"],
        "manifest_hash": manifest_hash(manifest),
        "dimensions": dict(manifest["dimensions"]),
        "cell_count": len(manifest["cells"]),
        "deposit_count": len(manifest["deposits"]),
        "water_steps": len(manifest["ledgers"]["water"]),
        "material_operations": len(manifest["ledgers"]["material_transfers"]),
    }


def save(manifest: Mapping[str, Any], path: str | os.PathLike[str]) -> dict[str, Any]:
    validate_manifest(manifest)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(manifest), sort_keys=True, indent=2, allow_nan=False))
    return {"path": str(target), "manifest_hash": manifest_hash(manifest)}


def resume(path: str | os.PathLike[str]) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(manifest)
    return manifest


def replay(manifest_or_path: Mapping[str, Any] | str | os.PathLike[str], operations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    state = resume(manifest_or_path) if isinstance(manifest_or_path, (str, os.PathLike)) else copy.deepcopy(dict(manifest_or_path))
    for operation in operations:
        kind = operation.get("kind")
        args = dict(operation)
        args.pop("kind", None)
        if kind == "soil_step":
            state = soil_step(state, **args)
        elif kind == "extract":
            state = extract(state, **args)
        elif kind == "excavate":
            state = excavate(state, **args)
        elif kind == "deposit":
            state = deposit(state, **args)
        else:
            raise ValueError(f"unknown replay operation: {kind}")
    return state


__all__ = [
    "CONTRACT_VERSION", "GENERATOR_VERSION", "MATERIALS", "PRESETS", "ConflictError",
    "preset_config", "validate_config", "generate", "validate_manifest", "manifest_hash",
    "generate_order_invariant", "extract", "excavate", "deposit", "soil_step", "inspect",
    "save", "resume", "replay",
]
