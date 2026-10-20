"""Strict bootstrap configuration; budgets are declarations, not a scheduler."""
import math
import tomllib
from pathlib import Path


def _number(value, low, high, name, integer=False):
    expected = (int,) if integer else (int, float)
    if type(value) not in expected or not low <= value <= high or not math.isfinite(value):
        raise ValueError(f"{name} must be {'integer ' if integer else ''}in [{low},{high}]")


def validate(config):
    expected = {
        "world": {"width_m", "height_m", "dt_s", "population", "population_limit"},
        "cognition": {"provider", "interval_ticks", "max_concurrency", "max_input_tokens",
                      "max_output_tokens", "timeout_s", "calls_per_simulated_day"},
        "logging": {"level", "event_retention_count", "max_payload_bytes"},
    }
    if set(config) - {"agency", "laws", "thermal", "culture", "execution", "ecology"} != {"schema_version", "seed", "mode", *expected}:
        raise ValueError("unknown or missing configuration keys")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("unsupported schema_version")
    _number(config["seed"], 0, 2**64 - 1, "seed", True)
    if config["mode"] not in ("closed", "guided"):
        raise ValueError("mode must be closed or guided")
    if "laws" in config:
        if type(config["laws"]) is not dict or set(config["laws"]) != {"hearing_range_m"}:
            raise ValueError("unknown law fields")
        _number(config["laws"]["hearing_range_m"],1,12,"hearing_range_m")
    for section, keys in expected.items():
        if not isinstance(config[section], dict) or set(config[section]) != keys:
            raise ValueError(f"unknown or missing {section} keys")
    world, cognition, logging = (config[key] for key in expected)
    for key in ("width_m", "height_m"):
        _number(world[key], 8, 1024, key)
    _number(world["dt_s"], .01, 1, "dt_s")
    _number(world["population_limit"], 1, 64, "population_limit", True)
    _number(world["population"], 1, world["population_limit"], "population", True)
    if cognition["provider"] not in ("disabled", "baseline", "llama.cpp"):
        raise ValueError("unknown cognition provider")
    if cognition["max_concurrency"] != 1:
        raise ValueError("Phase 3 supports one inference at a time")
    for key, low, high in (("interval_ticks", 1, 100000), ("max_concurrency", 1, 4),
                          ("max_input_tokens", 1, 8192), ("max_output_tokens", 1, 1024),
                          ("calls_per_simulated_day", 0, 10000)):
        _number(cognition[key], low, high, key, True)
    _number(cognition["timeout_s"], .1, 60, "timeout_s")
    if logging["level"] not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        raise ValueError("unsupported log level")
    _number(logging["event_retention_count"], 1, 100000, "event_retention_count", True)
    _number(logging["max_payload_bytes"], 256, 65536, "max_payload_bytes", True)
    if "agency" in config:
        agency=config["agency"]
        keys={"bodies_enabled","policy","interval_ticks","food_kg","water_kg","food_regen_kg_s","water_regen_kg_s","tree_growth_kg_s"}
        if type(agency) is not dict or set(agency)!=keys:raise ValueError("unknown or missing agency fields")
        if type(agency["bodies_enabled"]) is not bool or agency["policy"] not in ("none","utility"):
            raise ValueError("invalid body/policy configuration")
        if agency["policy"]=="utility" and not agency["bodies_enabled"]:raise ValueError("utility policy requires bodies")
        _number(agency["interval_ticks"],1,1000,"agency interval_ticks",True)
        for kind in ("food","water"):
            _number(agency[kind+"_kg"],0,1000,kind+"_kg")
            _number(agency[kind+"_regen_kg_s"],0,.01,kind+"_regen_kg_s")
        _number(agency["tree_growth_kg_s"],0,.01,"tree_growth_kg_s")
    if "ecology" in config:
        ecology=config["ecology"]
        if type(ecology) is not dict or set(ecology)!={"enabled","forage_kg","regeneration_kg_s"}:
            raise ValueError("unknown or missing ecology fields")
        if type(ecology["enabled"]) is not bool:raise ValueError("ecology enabled must be boolean")
        _number(ecology["forage_kg"],0,2,"forage_kg")
        _number(ecology["regeneration_kg_s"],0,.01,"regeneration_kg_s")
        if ecology["enabled"] and not config.get("agency",{}).get("bodies_enabled"):
            raise ValueError("ecology requires bodies")
    if "thermal" in config:
        thermal=config["thermal"]
        if type(thermal) is not dict or set(thermal)!={"enabled","open_boundaries","water_kg","fuel_kg","oxygen_kg","temperature_k"}:
            raise ValueError("unknown or missing thermal fields")
        if type(thermal["enabled"]) is not bool or type(thermal["open_boundaries"]) is not bool:
            raise ValueError("thermal switches must be boolean")
        for key in ("water_kg","fuel_kg","oxygen_kg"):
            _number(thermal[key],0,.05,key)
            if abs(thermal[key]*1e9-round(thermal[key]*1e9))>1e-5:raise ValueError("thermal mass resolution is 1 microgram")
        _number(thermal["temperature_k"],250,500,"temperature_k")
        if thermal["enabled"] and (not config.get("agency",{}).get("bodies_enabled") or min(world["width_m"],world["height_m"])<12 or config["agency"]["water_kg"]<4*thermal["water_kg"]):
            raise ValueError("thermal lab requires bodies, >=12m bounds and enough water")
    if "culture" in config:
        culture=config["culture"]
        if type(culture) is not dict or set(culture)!={"enabled","apparatus_seed","episodic_memory"}:
            raise ValueError("unknown or missing culture fields")
        if type(culture["enabled"]) is not bool or type(culture["episodic_memory"]) is not bool:
            raise ValueError("culture switches must be boolean")
        _number(culture["apparatus_seed"],0,2**64-1,"apparatus_seed",True)
        if culture["enabled"] and not config.get("thermal",{}).get("enabled"):
            raise ValueError("culture requires the thermal laboratory")
    if "execution" in config:
        limits={"batch_ticks":(1,1000),"epoch_ticks":(10,10000),"checkpoint_keep":(1,4),
            "max_db_bytes":(1048576,268435456),"max_archive_bytes":(1048576,536870912),
            "metrics_keep":(8,512),"memory_recent":(4,128),"queue_limit":(1,64),
            "calls_per_batch":(0,8),"cognition_call_limit":(0,1024)}
        if type(config["execution"]) is not dict or set(config["execution"])!=set(limits)|{"episodic_memory"}:raise ValueError("unknown or missing execution fields")
        if type(config["execution"]["episodic_memory"]) is not bool:raise ValueError("episodic_memory must be boolean")
        for key,(low,high) in limits.items():_number(config["execution"][key],low,high,key,True)
        if config["execution"]["epoch_ticks"]<config["execution"]["batch_ticks"]:raise ValueError("epoch must cover at least one batch")
    return config


def load(path):
    with Path(path).open("rb") as stream:
        return validate(tomllib.load(stream))


def episodic_enabled(config):
    return config.get("culture",{}).get("episodic_memory",True) and config.get("execution",{}).get("episodic_memory",True)
