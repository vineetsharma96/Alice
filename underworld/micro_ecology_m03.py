"""Bounded CPU-first M0-M3 microbial ecology sidecar.

This module is deliberately independent from the native engine and all existing
world/save formats.  It models aggregate functional guilds in explicit habitats,
with finite organic substrate, available nutrients, biomass, dead biomass and
products.  Transforms are copy-on-write and JSON-friendly so experiments can be
copied, resumed and replayed without creating a second legacy decomposition
backend.

The numerical model is an engineering approximation: organic carrier mass is
tracked in kilograms, N/P/K are tracked as separate element pools, and rates are
bounded by substrate, environmental factors and a one-hour numerical substep.
No ALIEN source is reused here; only the general idea of bounded aggregate
populations is adapted conceptually.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


RULE = "alice.micro-ecology.m03/v1"
VERSION = "m03.1"
EPSILON = 1e-10
MAX_HABITATS = 256
MAX_TRANSFER_EVENTS = 4096
MAX_INOCULUM_SOURCES = 16
MAX_STEP_S = 31 * 86400.0
SUBSTEP_S = 3600.0
NUTRIENTS = ("N", "P", "K")
HABITAT_KINDS = ("soil", "litter", "water", "food", "container", "host")
GUILDS = (
    "aerobic_decomposer",
    "low_oxygen_decomposer",
    "yeast_fermenter",
    "acid_producer",
)
SUBSTRATE_DEFAULT_NUTRIENTS = {
    "plant_litter": {"N": 0.018, "P": 0.0025, "K": 0.006},
    "deadwood": {"N": 0.006, "P": 0.001, "K": 0.002},
    "root_exudate": {"N": 0.012, "P": 0.0015, "K": 0.004},
    "food": {"N": 0.025, "P": 0.004, "K": 0.008},
    "dissolved_organic": {"N": 0.015, "P": 0.002, "K": 0.004},
    "host_waste": {"N": 0.03, "P": 0.004, "K": 0.01},
    "generic_organic": {"N": 0.01, "P": 0.002, "K": 0.004},
}
GUILD_SPECS = {
    "aerobic_decomposer": {
        "oxygen_optimum": 0.88,
        "oxygen_width": 0.42,
        "temperature_optimum_c": 27.0,
        "temperature_width_c": 18.0,
        "moisture_optimum": 0.64,
        "moisture_width": 0.72,
        "uptake_per_day": 0.95,
        "maintenance_per_day": 0.075,
        "mortality_per_day": 0.012,
        "yield": 0.55,
        "substrates": ("plant_litter", "deadwood", "root_exudate", "food", "host_waste", "generic_organic"),
    },
    "low_oxygen_decomposer": {
        "oxygen_optimum": 0.22,
        "oxygen_width": 0.48,
        "temperature_optimum_c": 24.0,
        "temperature_width_c": 20.0,
        "moisture_optimum": 0.78,
        "moisture_width": 0.68,
        "uptake_per_day": 0.70,
        "maintenance_per_day": 0.06,
        "mortality_per_day": 0.015,
        "yield": 0.48,
        "substrates": ("plant_litter", "deadwood", "root_exudate", "dissolved_organic", "host_waste", "generic_organic"),
    },
    "yeast_fermenter": {
        "oxygen_optimum": 0.30,
        "oxygen_width": 0.72,
        "temperature_optimum_c": 25.0,
        "temperature_width_c": 16.0,
        "moisture_optimum": 0.80,
        "moisture_width": 0.70,
        "uptake_per_day": 0.82,
        "maintenance_per_day": 0.052,
        "mortality_per_day": 0.01,
        "yield": 0.42,
        "substrates": ("food", "dissolved_organic", "root_exudate", "generic_organic"),
    },
    "acid_producer": {
        "oxygen_optimum": 0.38,
        "oxygen_width": 0.68,
        "temperature_optimum_c": 23.0,
        "temperature_width_c": 17.0,
        "moisture_optimum": 0.76,
        "moisture_width": 0.72,
        "uptake_per_day": 0.64,
        "maintenance_per_day": 0.058,
        "mortality_per_day": 0.014,
        "yield": 0.40,
        "substrates": ("food", "dissolved_organic", "plant_litter", "generic_organic"),
    },
}
FORBIDDEN_FIELD_TOKENS = ("private", "operator", "model", "secret", "hidden", "llm", "prompt")


class EcologyConflictError(ValueError):
    """Raised when a caller supplies a stale revision."""


def _reject_forbidden(value: Any, label: str = "value") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{label} fields must be strings")
            lowered = key.lower()
            if any(token in lowered for token in FORBIDDEN_FIELD_TOKENS):
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


def _text(value: Any, label: str, max_length: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ValueError(f"{label} must be a non-empty short string")
    return value


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def state_hash(state: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(state))
    body.pop("state_hash", None)
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def _nutrient_dict(values: Mapping[str, Any] | None = None) -> dict[str, float]:
    values = values or {}
    return {key: _number(values.get(key, 0.0), f"nutrient {key}") for key in NUTRIENTS}


def _substrate_record(name: str, value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        mass = value.get("mass_kg", value.get("mass", 0.0))
        nutrients = value.get("nutrients", SUBSTRATE_DEFAULT_NUTRIENTS.get(name, SUBSTRATE_DEFAULT_NUTRIENTS["generic_organic"]))
        accessibility = value.get("accessibility", 0.8)
    else:
        mass = value
        nutrients = SUBSTRATE_DEFAULT_NUTRIENTS.get(name, SUBSTRATE_DEFAULT_NUTRIENTS["generic_organic"])
        accessibility = 0.8
    return {
        "mass_kg": _number(mass, f"substrate {name} mass"),
        "nutrients": _nutrient_dict(nutrients),
        "accessibility": _number(accessibility, f"substrate {name} accessibility", 0.0, 1.0),
    }


def _population(guild: str, biomass: float, lineage_id: str, source: str) -> dict[str, Any]:
    return {
        "guild": guild,
        "lineage_id": lineage_id,
        "trait_version": VERSION,
        "biomass_kg": _number(biomass, f"{guild} biomass"),
        "reserves_kg": 0.0,
        "nutrients": _nutrient_dict(),
        "activity": "active" if biomass > EPSILON else "dormant",
        "division_progress": 0.0,
        "division_events": 0,
        "inoculum_sources": [source],
    }


def _default_habitats() -> dict[str, dict[str, Any]]:
    return {
        "soil-1": {"kind": "soil", "substrates": {"plant_litter": 2.0, "root_exudate": 0.3}, "available_nutrients": {"N": 0.04, "P": 0.01, "K": 0.02}, "temperature_c": 20.0, "moisture": 0.58, "oxygen": 0.85},
        "litter-1": {"kind": "litter", "substrates": {"plant_litter": 1.5, "deadwood": 1.0}, "temperature_c": 19.0, "moisture": 0.62, "oxygen": 0.78},
        "water-1": {"kind": "water", "substrates": {"dissolved_organic": 0.5}, "temperature_c": 18.0, "moisture": 1.0, "oxygen": 0.72},
        "food-1": {"kind": "food", "substrates": {"food": 0.75}, "temperature_c": 22.0, "moisture": 0.7, "oxygen": 0.55},
        "container-1": {"kind": "container", "substrates": {}, "temperature_c": 22.0, "moisture": 0.5, "oxygen": 0.5},
    }


def _normalize_habitats(habitats: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    raw = _default_habitats() if habitats is None else habitats
    if isinstance(raw, Mapping):
        items = []
        for habitat_id, spec in raw.items():
            item = dict(spec) if isinstance(spec, Mapping) else {}
            item.setdefault("habitat_id", habitat_id)
            items.append(item)
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        items = [dict(item) for item in raw]
    else:
        raise ValueError("habitats must be a mapping or sequence")
    if not items or len(items) > MAX_HABITATS:
        raise ValueError("habitat count is outside bounded M03 range")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _reject_forbidden(item, "habitat")
        habitat_id = _text(item.get("habitat_id", item.get("id")), "habitat_id")
        kind = item.get("kind", "soil")
        if kind not in HABITAT_KINDS:
            raise ValueError(f"unsupported habitat kind: {kind}")
        env = dict(item.get("environment", {}))
        env.update({key: item[key] for key in ("temperature_c", "moisture", "oxygen") if key in item})
        environment = {
            "temperature_c": _number(env.get("temperature_c", 20.0), "temperature_c", -80.0, 100.0),
            "moisture": _number(env.get("moisture", 0.6), "moisture", 0.0, 1.0),
            "oxygen": _number(env.get("oxygen", 0.7), "oxygen", 0.0, 1.0),
        }
        raw_substrates = item.get("substrates", {})
        if not isinstance(raw_substrates, Mapping):
            raise ValueError("habitat substrates must be a mapping")
        substrates = {str(name): _substrate_record(str(name), value) for name, value in raw_substrates.items()}
        nutrients = item.get("available_nutrients", item.get("nutrients", {}))
        result[habitat_id] = {
            "habitat_id": habitat_id,
            "kind": kind,
            "environment": environment,
            "substrates": substrates,
            "available_nutrients": _nutrient_dict(nutrients),
            "populations": {},
            "dead_biomass_kg": 0.0,
            "dead_nutrients": _nutrient_dict(),
            "byproducts": {"co2_kg": 0.0, "soluble_organic_kg": 0.0, "acids_kg": 0.0, "fermentation_products_kg": 0.0},
            "events": [],
        }
    if len(result) != len(items):
        raise ValueError("habitat IDs must be unique")
    return result


def _totals(state: Mapping[str, Any]) -> tuple[float, dict[str, float]]:
    organic = 0.0
    nutrients = {key: 0.0 for key in NUTRIENTS}
    for habitat in state["habitats"].values():
        for record in habitat["substrates"].values():
            organic += record["mass_kg"]
            for key in NUTRIENTS:
                nutrients[key] += record["nutrients"][key]
        organic += habitat["dead_biomass_kg"]
        for key in NUTRIENTS:
            nutrients[key] += habitat["available_nutrients"][key] + habitat["dead_nutrients"][key]
        for population in habitat["populations"].values():
            organic += population["biomass_kg"] + population["reserves_kg"]
            for key in NUTRIENTS:
                nutrients[key] += population["nutrients"][key]
        organic += sum(habitat["byproducts"].values())
    return organic, nutrients


def _substrate_nutrients_take(record: dict[str, Any], amount: float) -> dict[str, float]:
    before = record["mass_kg"]
    fraction = 0.0 if before <= EPSILON else _clamp(amount / before)
    result = {key: record["nutrients"][key] * fraction for key in NUTRIENTS}
    record["mass_kg"] = max(0.0, before - amount)
    for key in NUTRIENTS:
        record["nutrients"][key] = max(0.0, record["nutrients"][key] - result[key])
    return result


def _add_source(population: dict[str, Any], source: str) -> None:
    if source not in population["inoculum_sources"]:
        population["inoculum_sources"].append(source)
        population["inoculum_sources"] = population["inoculum_sources"][-MAX_INOCULUM_SOURCES:]


def _environment_factor(habitat: Mapping[str, Any], guild: str) -> float:
    spec = GUILD_SPECS[guild]
    env = habitat["environment"]
    temperature = math.exp(-((env["temperature_c"] - spec["temperature_optimum_c"]) / spec["temperature_width_c"]) ** 2)
    moisture = max(0.0, 1.0 - abs(env["moisture"] - spec["moisture_optimum"]) / spec["moisture_width"])
    oxygen = math.exp(-((env["oxygen"] - spec["oxygen_optimum"]) / spec["oxygen_width"]) ** 2)
    return _clamp(temperature * moisture * oxygen)


def _substrate_limit(habitat: Mapping[str, Any], guild: str) -> tuple[float, str | None, float]:
    allowed = GUILD_SPECS[guild]["substrates"]
    candidates = [(name, record) for name, record in habitat["substrates"].items() if name in allowed and record["mass_kg"] > EPSILON]
    if not candidates:
        return 0.0, None, 0.0
    name, record = max(candidates, key=lambda pair: pair[1]["mass_kg"] * pair[1]["accessibility"])
    available = sum(record["mass_kg"] * record["accessibility"] for _, record in candidates)
    return _clamp(available / (available + 0.25)), name, available


def initial(seed: int = 0, habitats: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None, inocula: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Create a new bounded ecology experiment; no population is spontaneous."""
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    _reject_forbidden(habitats, "habitats")
    _reject_forbidden(inocula, "inocula")
    state = {
        "rule": RULE,
        "version": VERSION,
        "seed": seed,
        "revision": 0,
        "time_s": 0.0,
        "habitats": _normalize_habitats(habitats),
        "transfer_events": [],
        "ledgers": {"organic_initial_kg": 0.0, "nutrients_initial": {key: 0.0 for key in NUTRIENTS}, "organic_boundary_kg": 0.0, "nutrient_boundary": {key: 0.0 for key in NUTRIENTS}},
        "origin": "CPU aggregate M0-M3 sidecar; no legacy decomposition owner",
    }
    for item in inocula or ():
        if not isinstance(item, Mapping):
            raise ValueError("inoculum entries must be mappings")
        habitat_id = item.get("habitat_id", item.get("target_habitat"))
        guild = item.get("guild")
        biomass = item.get("biomass_kg", item.get("biomass"))
        source = item.get("source", "initial_inoculum")
        if not isinstance(habitat_id, str) or not isinstance(guild, str) or not isinstance(source, str):
            raise ValueError("inoculum requires habitat_id, guild and source")
        _inoculate_mutating(state, habitat_id, guild, biomass, source)
    organic, nutrients = _totals(state)
    state["ledgers"]["organic_initial_kg"] = organic
    state["ledgers"]["nutrients_initial"] = nutrients
    validate(state)
    return state


def validate(state: Mapping[str, Any]) -> dict[str, Any]:
    """Validate schema, positivity, identity boundaries and tracked conservation."""
    if not isinstance(state, Mapping):
        raise ValueError("ecology state must be a mapping")
    _reject_forbidden(state, "state")
    expected = {"rule", "version", "seed", "revision", "time_s", "habitats", "transfer_events", "ledgers", "origin"}
    if set(state) != expected or state["rule"] != RULE or state["version"] != VERSION:
        raise ValueError("unsupported M03 ecology schema")
    if type(state["seed"]) is not int or type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("invalid ecology identity or revision")
    _number(state["time_s"], "time_s")
    habitats = state["habitats"]
    if not isinstance(habitats, Mapping) or not habitats or len(habitats) > MAX_HABITATS:
        raise ValueError("invalid habitat set")
    for habitat_id, habitat in habitats.items():
        if habitat.get("habitat_id") != habitat_id or habitat.get("kind") not in HABITAT_KINDS:
            raise ValueError("invalid habitat identity")
        env = habitat["environment"]
        _number(env["temperature_c"], "temperature_c", -80.0, 100.0)
        for key in ("moisture", "oxygen"):
            _number(env[key], key, 0.0, 1.0)
        for record in habitat["substrates"].values():
            _number(record["mass_kg"], "substrate mass")
            _number(record["accessibility"], "accessibility", 0.0, 1.0)
            nutrients = record["nutrients"]
            if set(nutrients) != set(NUTRIENTS):
                raise ValueError("invalid substrate nutrient set")
            for value in nutrients.values():
                _number(value, "substrate nutrient")
        for key in ("dead_biomass_kg",):
            _number(habitat[key], key)
        for pool in (habitat["available_nutrients"], habitat["dead_nutrients"]):
            if set(pool) != set(NUTRIENTS):
                raise ValueError("invalid nutrient pool")
            for value in pool.values():
                _number(value, "nutrient pool")
        for value in habitat["byproducts"].values():
            _number(value, "byproduct")
        for guild, population in habitat["populations"].items():
            if guild not in GUILDS or population.get("guild") != guild or population.get("trait_version") != VERSION:
                raise ValueError("invalid microbial guild")
            _text(population["lineage_id"], "lineage_id")
            _number(population["biomass_kg"], "biomass")
            _number(population["reserves_kg"], "reserves")
            if population["activity"] not in ("active", "dormant"):
                raise ValueError("invalid population activity")
            _number(population["division_progress"], "division progress", 0.0, 1.0)
            if type(population["division_events"]) is not int or population["division_events"] < 0:
                raise ValueError("invalid division events")
            if not isinstance(population["inoculum_sources"], list) or len(population["inoculum_sources"]) > MAX_INOCULUM_SOURCES:
                raise ValueError("inoculum source bound exceeded")
            for source in population["inoculum_sources"]:
                _text(source, "inoculum source")
            nutrients = population["nutrients"]
            if set(nutrients) != set(NUTRIENTS):
                raise ValueError("invalid population nutrient set")
            for value in nutrients.values():
                _number(value, "population nutrient")
    if not isinstance(state["transfer_events"], list) or len(state["transfer_events"]) > MAX_TRANSFER_EVENTS:
        raise ValueError("transfer event budget exceeded")
    ledgers = state["ledgers"]
    _number(ledgers["organic_initial_kg"], "organic initial")
    _number(ledgers["organic_boundary_kg"], "organic boundary")
    for pool in (ledgers["nutrients_initial"], ledgers["nutrient_boundary"]):
        if set(pool) != set(NUTRIENTS):
            raise ValueError("invalid ledger nutrient set")
        for value in pool.values():
            _number(value, "ledger nutrient")
    organic, nutrients = _totals(state)
    if abs(organic - (ledgers["organic_initial_kg"] + ledgers["organic_boundary_kg"])) > 2e-8:
        raise ValueError("organic tracked-mass conservation failed")
    for key in NUTRIENTS:
        if abs(nutrients[key] - (ledgers["nutrients_initial"][key] + ledgers["nutrient_boundary"][key])) > 2e-8:
            raise ValueError(f"{key} tracked-mass conservation failed")
    return dict(state)


def _copy_checked(state: Mapping[str, Any]) -> dict[str, Any]:
    validate(state)
    return copy.deepcopy(dict(state))


def _inoculate_mutating(state: dict[str, Any], habitat_id: str, guild: str, biomass: float, source: str) -> None:
    if habitat_id not in state["habitats"]:
        raise ValueError("unknown inoculum habitat")
    if guild not in GUILDS:
        raise ValueError("unknown microbial guild")
    biomass = _number(biomass, "inoculum biomass")
    source = _text(source, "inoculum source")
    _reject_forbidden({"source": source}, "inoculum")
    habitat = state["habitats"][habitat_id]
    population = habitat["populations"].get(guild)
    if population is None:
        population = _population(guild, biomass, f"lineage-{state['seed']}-{guild}", source)
        habitat["populations"][guild] = population
    else:
        population["biomass_kg"] += biomass
        _add_source(population, source)
        population["activity"] = "active"


def inoculate(state: Mapping[str, Any], habitat_id: str, guild: str, biomass_kg: float, source: str = "explicit_inoculum", expected_revision: int | None = None) -> dict[str, Any]:
    """Add a declared source inoculum; this is the only way to seed sterile stock."""
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    _inoculate_mutating(result, habitat_id, guild, biomass_kg, source)
    result["revision"] += 1
    result["transfer_events"].append({"kind": "inoculum", "source": source, "target_habitat": habitat_id, "guild": guild, "biomass_kg": float(biomass_kg)})
    validate(result)
    return result


def transfer(state: Mapping[str, Any], source_habitat: str, target_habitat: str, guild: str, biomass_kg: float, source_id: str | None = None, expected_revision: int | None = None) -> dict[str, Any]:
    """Move viable aggregate biomass between connected habitats without duplication."""
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    if source_habitat not in result["habitats"] or target_habitat not in result["habitats"]:
        raise ValueError("unknown transfer habitat")
    if source_habitat == target_habitat or guild not in GUILDS:
        raise ValueError("invalid transfer route")
    if source_id is not None:
        _reject_forbidden({"source_id": source_id}, "transfer")
    amount = _number(biomass_kg, "transfer biomass")
    source = result["habitats"][source_habitat]["populations"].get(guild)
    if source is None or source["biomass_kg"] + EPSILON < amount:
        raise ValueError("transfer exceeds viable source biomass")
    target = result["habitats"][target_habitat]["populations"].get(guild)
    if target is None:
        target = _population(guild, 0.0, source["lineage_id"], source_id or f"transfer:{source_habitat}")
        result["habitats"][target_habitat]["populations"][guild] = target
    fraction = 0.0 if source["biomass_kg"] <= EPSILON else amount / source["biomass_kg"]
    reserve = source["reserves_kg"] * fraction
    nutrients = {key: source["nutrients"][key] * fraction for key in NUTRIENTS}
    source["biomass_kg"] -= amount
    source["reserves_kg"] -= reserve
    for key in NUTRIENTS:
        source["nutrients"][key] -= nutrients[key]
        target["nutrients"][key] += nutrients[key]
    target["biomass_kg"] += amount
    target["reserves_kg"] += reserve
    _add_source(target, source_id or f"transfer:{source_habitat}")
    target["activity"] = "active"
    source["activity"] = "dormant" if source["biomass_kg"] <= EPSILON else source["activity"]
    result["revision"] += 1
    result["transfer_events"].append({"kind": "transfer", "source_habitat": source_habitat, "target_habitat": target_habitat, "guild": guild, "biomass_kg": amount, "source_id": source_id or f"transfer:{source_habitat}"})
    validate(result)
    return result


def _move_dead_mutating(habitat: dict[str, Any], population: dict[str, Any], amount: float) -> None:
    if amount <= EPSILON:
        return
    fraction = 0.0 if population["biomass_kg"] <= EPSILON else min(1.0, amount / population["biomass_kg"])
    dead_nutrients = {key: population["nutrients"][key] * fraction for key in NUTRIENTS}
    population["biomass_kg"] = max(0.0, population["biomass_kg"] - amount)
    for key in NUTRIENTS:
        population["nutrients"][key] = max(0.0, population["nutrients"][key] - dead_nutrients[key])
        habitat["dead_nutrients"][key] += dead_nutrients[key]
    habitat["dead_biomass_kg"] += amount


def _consume_for_guild(habitat: dict[str, Any], population: dict[str, Any], guild: str, amount: float) -> float:
    remaining = amount
    consumed = 0.0
    for name in GUILD_SPECS[guild]["substrates"]:
        record = habitat["substrates"].get(name)
        if not record or record["mass_kg"] <= EPSILON:
            continue
        take = min(record["mass_kg"], max(0.0, remaining))
        nutrient_take = _substrate_nutrients_take(record, take)
        consumed += take
        remaining -= take * record["accessibility"]
        for key in NUTRIENTS:
            population["nutrients"][key] += nutrient_take[key] * 0.7
            habitat["available_nutrients"][key] += nutrient_take[key] * 0.3
        habitat["byproducts"]["soluble_organic_kg"] += take * 0.0
        if remaining <= EPSILON:
            break
    return consumed


def _step_sub(habitat: dict[str, Any], dt_s: float) -> None:
    dt_days = dt_s / 86400.0
    for guild, population in list(habitat["populations"].items()):
        biomass_before = population["biomass_kg"]
        if biomass_before <= EPSILON:
            population["biomass_kg"] = 0.0
            population["activity"] = "dormant"
            continue
        environmental = _environment_factor(habitat, guild)
        substrate_factor, _, available = _substrate_limit(habitat, guild)
        uptake_request = biomass_before * GUILD_SPECS[guild]["uptake_per_day"] * environmental * substrate_factor * dt_days
        consumed = _consume_for_guild(habitat, population, guild, uptake_request)
        spec = GUILD_SPECS[guild]
        biomass_gain = consumed * spec["yield"] * 0.72
        reserve_gain = consumed * spec["yield"] * 0.12
        product_mass = max(0.0, consumed - biomass_gain - reserve_gain)
        population["biomass_kg"] += biomass_gain
        population["reserves_kg"] += reserve_gain
        product_key = "fermentation_products_kg" if guild == "yeast_fermenter" else "acids_kg" if guild == "acid_producer" else "co2_kg"
        habitat["byproducts"][product_key] += product_mass
        population["division_progress"] += biomass_gain / max(biomass_before, 0.001)
        divisions = int(population["division_progress"])
        if divisions:
            population["division_events"] += divisions
            population["division_progress"] -= divisions
        maintenance = (population["biomass_kg"] + population["reserves_kg"]) * spec["maintenance_per_day"] * dt_days * (0.35 + 0.65 * environmental)
        reserve_use = min(population["reserves_kg"], maintenance)
        if reserve_use > EPSILON:
            reserve_fraction = reserve_use / max(population["biomass_kg"] + population["reserves_kg"], EPSILON)
            for key in NUTRIENTS:
                mineralized = population["nutrients"][key] * reserve_fraction
                population["nutrients"][key] -= mineralized
                habitat["available_nutrients"][key] += mineralized
            habitat["byproducts"]["co2_kg"] += reserve_use
        population["reserves_kg"] -= reserve_use
        maintenance_remaining = maintenance - reserve_use
        if maintenance_remaining > EPSILON:
            biomass_use = min(population["biomass_kg"], maintenance_remaining)
            fraction = biomass_use / max(population["biomass_kg"], EPSILON)
            for key in NUTRIENTS:
                mineralized = population["nutrients"][key] * fraction
                population["nutrients"][key] -= mineralized
                habitat["available_nutrients"][key] += mineralized
            population["biomass_kg"] -= biomass_use
            habitat["byproducts"]["co2_kg"] += biomass_use
        mortality = population["biomass_kg"] * spec["mortality_per_day"] * dt_days * (1.0 + 1.8 * (1.0 - environmental))
        if available <= EPSILON and population["reserves_kg"] <= EPSILON:
            mortality += population["biomass_kg"] * min(0.25, 0.08 * dt_days)
        mortality = min(population["biomass_kg"], max(0.0, mortality))
        _move_dead_mutating(habitat, population, mortality)
        population["activity"] = "active" if environmental >= 0.04 and (substrate_factor > 0.01 or population["reserves_kg"] > EPSILON) else "dormant"
        if population["biomass_kg"] <= EPSILON:
            population["biomass_kg"] = 0.0
            population["activity"] = "dormant"


def step(state: Mapping[str, Any], dt_s: float, expected_revision: int | None = None) -> dict[str, Any]:
    """Advance all habitats using bounded one-hour substeps."""
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    dt_s = _number(dt_s, "step dt_s", 0.0, MAX_STEP_S)
    result = _copy_checked(state)
    remaining = dt_s
    while remaining > EPSILON:
        substep = min(SUBSTEP_S, remaining)
        for habitat in result["habitats"].values():
            _step_sub(habitat, substep)
        result["time_s"] += substep
        remaining -= substep
    result["revision"] += 1
    validate(result)
    return result


def decompose(state: Mapping[str, Any], habitat_id: str, substrate: str, mass_kg: float, expected_revision: int | None = None) -> dict[str, Any]:
    """Decompose finite litter/dead biomass and return nutrients/products.

    This explicit transform is useful for plant-litter fixtures.  It does not
    create a microbial population; use ``inoculate`` and ``step`` for growth.
    """
    if expected_revision is not None and state.get("revision") != expected_revision:
        raise EcologyConflictError("ecology revision is stale")
    result = _copy_checked(state)
    if habitat_id not in result["habitats"]:
        raise ValueError("unknown decomposition habitat")
    amount = _number(mass_kg, "decomposition mass")
    habitat = result["habitats"][habitat_id]
    if substrate == "dead_biomass":
        available = habitat["dead_biomass_kg"]
        if amount > available + EPSILON:
            raise ValueError("decomposition exceeds dead biomass")
        fraction = 0.0 if available <= EPSILON else amount / available
        habitat["dead_biomass_kg"] -= amount
        for key in NUTRIENTS:
            released = habitat["dead_nutrients"][key] * fraction
            habitat["dead_nutrients"][key] -= released
            habitat["available_nutrients"][key] += released
    else:
        record = habitat["substrates"].get(substrate)
        if record is None or amount > record["mass_kg"] + EPSILON:
            raise ValueError("decomposition exceeds finite substrate")
        nutrient_take = _substrate_nutrients_take(record, amount)
        for key in NUTRIENTS:
            habitat["available_nutrients"][key] += nutrient_take[key]
    habitat["byproducts"]["soluble_organic_kg"] += amount * 0.78
    habitat["byproducts"]["co2_kg"] += amount * 0.22
    habitat["events"].append({"kind": "decompose", "substrate": substrate, "mass_kg": amount})
    habitat["events"] = habitat["events"][-128:]
    result["revision"] += 1
    validate(result)
    return result


def inspect(state: Mapping[str, Any], habitat_id: str | None = None) -> dict[str, Any]:
    """Return observer-facing aggregate ecology without private/model fields."""
    validate(state)
    if habitat_id is not None:
        if habitat_id not in state["habitats"]:
            raise ValueError("unknown inspection habitat")
        selected = {habitat_id: state["habitats"][habitat_id]}
    else:
        selected = state["habitats"]
    habitats = []
    for item in selected.values():
        habitats.append({
            "habitat_id": item["habitat_id"],
            "kind": item["kind"],
            "environment": copy.deepcopy(item["environment"]),
            "substrate_mass_kg": sum(record["mass_kg"] for record in item["substrates"].values()),
            "available_nutrients": copy.deepcopy(item["available_nutrients"]),
            "biomass_kg": sum(pop["biomass_kg"] for pop in item["populations"].values()),
            "dead_biomass_kg": item["dead_biomass_kg"],
            "guilds": {guild: {"biomass_kg": pop["biomass_kg"], "activity": pop["activity"], "lineage_id": pop["lineage_id"], "division_events": pop["division_events"]} for guild, pop in item["populations"].items()},
            "byproducts": copy.deepcopy(item["byproducts"]),
        })
    organic, nutrients = _totals(state)
    return {"rule": RULE, "revision": state["revision"], "time_s": state["time_s"], "habitats": habitats, "tracked_organic_kg": organic, "tracked_nutrients": nutrients, "state_hash": state_hash(state)}


def save(state: Mapping[str, Any], path: str | Path) -> dict[str, Any]:
    """Write one validated JSON checkpoint without changing the source state."""
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
    """Load and validate a JSON checkpoint, rejecting tampered payloads."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    recorded = payload.pop("state_hash", None)
    if recorded != state_hash(payload):
        raise ValueError("ecology checkpoint checksum mismatch")
    validate(payload)
    return payload


def replay(state: Mapping[str, Any], commands: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Replay explicit sidecar commands from a validated starting checkpoint."""
    result = _copy_checked(state)
    for command in commands:
        _reject_forbidden(command, "command")
        kind = command.get("kind")
        if kind == "step":
            result = step(result, command["dt_s"])
        elif kind == "inoculate":
            result = inoculate(result, command["habitat_id"], command["guild"], command["biomass_kg"], command.get("source", "replay"))
        elif kind == "transfer":
            result = transfer(result, command["source_habitat"], command["target_habitat"], command["guild"], command["biomass_kg"], command.get("source_id"))
        elif kind == "decompose":
            result = decompose(result, command["habitat_id"], command["substrate"], command["mass_kg"])
        else:
            raise ValueError(f"unknown ecology replay command: {kind}")
    return result


__all__ = [
    "RULE", "VERSION", "GUILDS", "HABITAT_KINDS", "EcologyConflictError",
    "initial", "validate", "step", "transfer", "inoculate", "decompose",
    "inspect", "save", "resume", "replay", "state_hash",
]
