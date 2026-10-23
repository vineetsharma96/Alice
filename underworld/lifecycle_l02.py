"""Bounded, copy-friendly lifecycle/reproduction foundation for ALICE 02.

This module is deliberately a pure JSON state machine.  It does not import the
native engine or ``storage.py`` and it never executes a world action.  Callers
may use the returned ``*_proposal`` values with an external/native authority,
then apply the resulting explicit decision to a copied state.

The implementation covers the durable L0-L4 contracts plus the small trait and
care records needed to make a birth auditable.  It is not a claim about
subjective love, consciousness, or autonomous reproductive behavior.
"""

from copy import deepcopy
import hashlib
import json
import math
import random
import re


RULE = "alice-lifecycle-l02-1"
SCHEMA_VERSION = 1
MAX_EVIDENCE = 32
MAX_INDIVIDUALS = 256
MAX_TRAITS = 4
MAX_ID_LENGTH = 128
MAX_EVENT_ID_LENGTH = 160
IDENTITY_VALUES = frozenset({"male", "female", "nonbinary", "unknown", "unassigned"})
BIOLOGICAL_ROLES = frozenset({"male", "female", "dual", "asexual", "none"})
TRAIT_RANGES = {
    "body_size_potential": (0.0, 1.0),
    "metabolic_efficiency": (0.0, 1.0),
    "maturation_tendency": (0.0, 1.0),
    "sensory_sensitivity": (0.0, 1.0),
}
EVIDENCE_KINDS = frozenset({
    "familiarity", "trust", "affection", "attraction", "attachment",
    "shared_activity", "reliable_help", "responsiveness", "safety",
    "invitation_accepted", "invitation_declined",
})
FORBIDDEN_PARTS = (
    "private", "hidden", "secret", "operator", "model", "llm", "prompt",
    "target_state", "foreign_state", "self_report",
)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _id(value, label="identifier"):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid lifecycle {label}")
    return value


def _event_id(value):
    if type(value) is not str or not value or len(value) > MAX_EVENT_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError("Invalid lifecycle event identity")
    return value


def _finite(value, label, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"Invalid lifecycle {label}")
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"Invalid lifecycle {label}")
    return value


def _nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid lifecycle {label}")
    return value


def _reject_forbidden(value, label="value"):
    """Reject operator/model/private escape hatches in public envelopes."""
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid lifecycle {label} field")
            lowered = key.lower()
            if any(part in lowered for part in FORBIDDEN_PARTS):
                raise ValueError("Lifecycle private, operator, and model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item, label)
    elif isinstance(value, tuple):
        raise ValueError(f"Lifecycle {label} must be JSON-copyable")


def _bounded_traits(traits, label="traits"):
    if type(traits) is not dict or set(traits) != set(TRAIT_RANGES):
        raise ValueError(f"Lifecycle {label} must contain the bounded trait schema")
    result = {}
    for key, (low, high) in TRAIT_RANGES.items():
        result[key] = _finite(traits[key], f"{label}.{key}", low, high)
    return result


def life_stage(stage_id, min_age_steps, max_age_steps, can_reproduce, capabilities=None):
    """Create a versioned age-stage contract."""
    stage_id = _id(stage_id, "stage_id")
    min_age_steps = _nonnegative_int(min_age_steps, "minimum age")
    if max_age_steps is not None:
        max_age_steps = _nonnegative_int(max_age_steps, "maximum age")
        if max_age_steps < min_age_steps:
            raise ValueError("Lifecycle stage age range is reversed")
    if type(can_reproduce) is not bool:
        raise ValueError("Lifecycle stage reproduction flag must be boolean")
    capabilities = {} if capabilities is None else deepcopy(capabilities)
    _reject_forbidden(capabilities, "stage capabilities")
    if type(capabilities) is not dict:
        raise ValueError("Lifecycle stage capabilities must be a mapping")
    result = {"schema": "LifeStage", "version": SCHEMA_VERSION, "stage_id": stage_id,
              "min_age_steps": min_age_steps, "max_age_steps": max_age_steps,
              "can_reproduce": can_reproduce, "capabilities": capabilities}
    validate_life_stage(result)
    return result


def validate_life_stage(stage):
    expected = {"schema", "version", "stage_id", "min_age_steps", "max_age_steps",
                "can_reproduce", "capabilities"}
    if type(stage) is not dict or set(stage) != expected or stage["schema"] != "LifeStage" or stage["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported LifeStage contract")
    _id(stage["stage_id"], "stage_id")
    _nonnegative_int(stage["min_age_steps"], "minimum age")
    if stage["max_age_steps"] is not None:
        _nonnegative_int(stage["max_age_steps"], "maximum age")
        if stage["max_age_steps"] < stage["min_age_steps"]:
            raise ValueError("Lifecycle stage age range is reversed")
    if type(stage["can_reproduce"]) is not bool or type(stage["capabilities"]) is not dict:
        raise ValueError("Invalid LifeStage contract")
    _reject_forbidden(stage["capabilities"], "stage capabilities")
    return stage


def reproductive_profile(profile_id, species_id, biological_role, compatible_roles,
                         maturity_stage, gestation_steps, resource_cost_per_step,
                         conception_probability=1.0, reproductive_system="sexual",
                         refractory_steps=0):
    """Create a species-specific reproductive physiology contract."""
    profile_id, species_id = _id(profile_id, "profile_id"), _id(species_id, "species_id")
    if biological_role not in BIOLOGICAL_ROLES:
        raise ValueError("Invalid biological reproductive role")
    if type(compatible_roles) not in (list, tuple) or not compatible_roles:
        raise ValueError("Compatible biological roles are required")
    compatible_roles = list(dict.fromkeys(compatible_roles))
    if any(role not in BIOLOGICAL_ROLES for role in compatible_roles):
        raise ValueError("Invalid compatible biological role")
    maturity_stage = _id(maturity_stage, "maturity stage")
    _nonnegative_int(gestation_steps, "gestation")
    if gestation_steps < 1 and reproductive_system in {"sexual", "dual"}:
        raise ValueError("Sexual gestation must consume elapsed biological time")
    _nonnegative_int(refractory_steps, "refractory interval")
    _finite(conception_probability, "conception probability", 0.0, 1.0)
    if reproductive_system not in {"sexual", "asexual", "dual", "none"}:
        raise ValueError("Invalid reproductive system")
    if type(resource_cost_per_step) is not dict or not resource_cost_per_step:
        raise ValueError("Lifecycle resource cost must be a mapping")
    resource_cost = {}
    for resource, amount in resource_cost_per_step.items():
        resource_cost[_id(resource, "resource")] = _finite(amount, "resource cost", 0.0)
    result = {"schema": "ReproductiveProfile", "version": SCHEMA_VERSION,
              "profile_id": profile_id, "species_id": species_id,
              "biological_role": biological_role, "compatible_roles": compatible_roles,
              "maturity_stage": maturity_stage, "gestation_steps": gestation_steps,
              "resource_cost_per_step": resource_cost,
              "conception_probability": float(conception_probability),
              "reproductive_system": reproductive_system,
              "refractory_steps": refractory_steps}
    validate_reproductive_profile(result)
    return result


def validate_reproductive_profile(profile):
    expected = {"schema", "version", "profile_id", "species_id", "biological_role",
                "compatible_roles", "maturity_stage", "gestation_steps",
                "resource_cost_per_step", "conception_probability", "reproductive_system",
                "refractory_steps"}
    if type(profile) is not dict or set(profile) != expected or profile["schema"] != "ReproductiveProfile" or profile["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported ReproductiveProfile contract")
    _id(profile["profile_id"], "profile_id"); _id(profile["species_id"], "species_id")
    if profile["biological_role"] not in BIOLOGICAL_ROLES:
        raise ValueError("Invalid biological reproductive role")
    if profile["biological_role"] == "none" and profile["reproductive_system"] != "none":
        raise ValueError("Non-reproductive role cannot use a reproductive system")
    if profile["biological_role"] == "asexual" and profile["reproductive_system"] not in {"asexual", "dual"}:
        raise ValueError("Asexual role requires an asexual-capable system")
    if profile["biological_role"] in {"male", "female"} and profile["reproductive_system"] not in {"sexual", "dual"}:
        raise ValueError("Male/female role requires a sexual-capable system")
    if type(profile["compatible_roles"]) is not list or not profile["compatible_roles"] or any(role not in BIOLOGICAL_ROLES for role in profile["compatible_roles"]):
        raise ValueError("Invalid compatible biological roles")
    _id(profile["maturity_stage"], "maturity stage")
    _nonnegative_int(profile["gestation_steps"], "gestation")
    if profile["gestation_steps"] < 1 and profile["reproductive_system"] in {"sexual", "dual"}:
        raise ValueError("Sexual gestation must consume elapsed biological time")
    _nonnegative_int(profile["refractory_steps"], "refractory interval")
    _finite(profile["conception_probability"], "conception probability", 0.0, 1.0)
    if profile["reproductive_system"] not in {"sexual", "asexual", "dual", "none"}:
        raise ValueError("Invalid reproductive system")
    if profile["biological_role"] == "none" and profile["reproductive_system"] != "none":
        raise ValueError("Non-reproductive role cannot use a reproductive system")
    if profile["biological_role"] == "asexual" and profile["reproductive_system"] not in {"asexual", "dual"}:
        raise ValueError("Asexual role requires an asexual-capable system")
    if profile["biological_role"] in {"male", "female"} and profile["reproductive_system"] not in {"sexual", "dual"}:
        raise ValueError("Male/female role requires a sexual-capable system")
    if type(profile["resource_cost_per_step"]) is not dict or not profile["resource_cost_per_step"]:
        raise ValueError("Invalid resource costs")
    for resource, amount in profile["resource_cost_per_step"].items():
        _id(resource, "resource"); _finite(amount, "resource cost", 0.0)
    return profile


def species_lifecycle(species_id, stages, reproductive_profiles, time_unit="biological_step", max_age_steps=None):
    """Create a species lifecycle contract with one declared biological clock."""
    species_id = _id(species_id, "species_id")
    if type(stages) not in (list, tuple) or not stages:
        raise ValueError("Species lifecycle needs at least one stage")
    stages = [deepcopy(stage) for stage in stages]
    for stage in stages:
        validate_life_stage(stage)
    stage_ids = [stage["stage_id"] for stage in stages]
    if len(stage_ids) != len(set(stage_ids)) or stages[0]["min_age_steps"] != 0:
        raise ValueError("Lifecycle stages must be unique and start at age zero")
    if type(reproductive_profiles) not in (list, tuple) or not reproductive_profiles:
        raise ValueError("Species lifecycle needs reproductive profiles")
    reproductive_profiles = [deepcopy(profile) for profile in reproductive_profiles]
    for profile in reproductive_profiles:
        validate_reproductive_profile(profile)
        if profile["species_id"] != species_id or profile["maturity_stage"] not in stage_ids:
            raise ValueError("Reproductive profile does not match species stages")
    if type(time_unit) is not str or not time_unit or len(time_unit) > 64:
        raise ValueError("Invalid lifecycle time unit")
    if max_age_steps is not None:
        _nonnegative_int(max_age_steps, "maximum age")
    result = {"schema": "SpeciesLifecycle", "version": SCHEMA_VERSION,
              "species_id": species_id, "time_unit": time_unit,
              "stages": stages, "reproductive_profiles": reproductive_profiles,
              "max_age_steps": max_age_steps}
    validate_species_lifecycle(result)
    return result


def validate_species_lifecycle(contract):
    expected = {"schema", "version", "species_id", "time_unit", "stages",
                "reproductive_profiles", "max_age_steps"}
    if type(contract) is not dict or set(contract) != expected or contract["schema"] != "SpeciesLifecycle" or contract["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported SpeciesLifecycle contract")
    _id(contract["species_id"], "species_id")
    if type(contract["time_unit"]) is not str or not contract["time_unit"]:
        raise ValueError("Invalid lifecycle time unit")
    if type(contract["stages"]) is not list or not contract["stages"]:
        raise ValueError("Invalid lifecycle stages")
    for stage in contract["stages"]:
        validate_life_stage(stage)
    if contract["stages"][0]["min_age_steps"] != 0:
        raise ValueError("Lifecycle stages must start at age zero")
    if type(contract["reproductive_profiles"]) is not list or not contract["reproductive_profiles"]:
        raise ValueError("Invalid reproductive profiles")
    for profile in contract["reproductive_profiles"]:
        validate_reproductive_profile(profile)
        if profile["species_id"] != contract["species_id"]:
            raise ValueError("Foreign reproductive profile")
    if contract["max_age_steps"] is not None:
        _nonnegative_int(contract["max_age_steps"], "maximum age")
    return contract


def lineage(child_id, parents, inherited_traits, mutations, birth_event_id):
    """Create traceable lineage metadata without copying parental knowledge."""
    child_id = _id(child_id, "child_id")
    if type(parents) is not list or len(parents) not in (0, 1, 2) or len(parents) != len(set(parents)):
        raise ValueError("Lineage requires zero, one, or two distinct parents")
    for parent in parents:
        _id(parent, "parent_id")
    inherited_traits = _bounded_traits(inherited_traits, "inherited traits")
    if type(mutations) is not dict or set(mutations) != set(TRAIT_RANGES):
        raise ValueError("Lineage mutations must use the bounded trait schema")
    mutations = {key: _finite(value, f"mutation.{key}", -1.0, 1.0) for key, value in mutations.items()}
    _event_id(birth_event_id)
    result = {"schema": "Lineage", "version": SCHEMA_VERSION, "child_id": child_id,
              "parents": list(parents), "inherited_traits": inherited_traits,
              "mutations": mutations, "birth_event_id": birth_event_id,
              "knowledge_provenance": "developmental experience only; no parental copy"}
    validate_lineage(result)
    return result


def validate_lineage(item):
    expected = {"schema", "version", "child_id", "parents", "inherited_traits",
                "mutations", "birth_event_id", "knowledge_provenance"}
    if type(item) is not dict or set(item) != expected or item["schema"] != "Lineage" or item["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported Lineage contract")
    _id(item["child_id"], "child_id")
    if type(item["parents"]) is not list or len(item["parents"]) not in (0, 1, 2) or len(item["parents"]) != len(set(item["parents"])):
        raise ValueError("Invalid lineage parents")
    for parent in item["parents"]:
        _id(parent, "parent_id")
    _bounded_traits(item["inherited_traits"], "inherited traits")
    if type(item["mutations"]) is not dict or set(item["mutations"]) != set(TRAIT_RANGES):
        raise ValueError("Invalid lineage mutations")
    for key, value in item["mutations"].items():
        _finite(value, f"mutation.{key}", -1.0, 1.0)
    _event_id(item["birth_event_id"])
    if item["knowledge_provenance"] != "developmental experience only; no parental copy":
        raise ValueError("Invalid lineage knowledge provenance")
    return item


def relationship_evidence(observer, target, evidence_id, kind, tick, value=1.0, uncertainty=1.0, provenance="observed"):
    """Create one directional, public/evidence-backed relationship observation."""
    observer, target = _id(observer, "observer"), _id(target, "target")
    if observer == target:
        raise ValueError("A relationship needs two distinct inhabitants")
    _event_id(evidence_id); _nonnegative_int(tick, "relationship tick")
    if kind not in EVIDENCE_KINDS:
        raise ValueError("Invalid relationship evidence kind")
    _finite(value, "relationship value", -1.0, 1.0)
    _finite(uncertainty, "relationship uncertainty", 0.0, 1.0)
    if provenance not in {"observed", "native_receipt", "public_report"}:
        raise ValueError("Invalid relationship evidence provenance")
    return {"schema": "RelationshipEvidence", "version": SCHEMA_VERSION,
            "observer": observer, "target": target, "evidence_id": evidence_id,
            "kind": kind, "tick": tick, "value": float(value),
            "uncertainty": float(uncertainty), "provenance": provenance}


def validate_relationship_evidence(item):
    expected = {"schema", "version", "observer", "target", "evidence_id", "kind",
                "tick", "value", "uncertainty", "provenance"}
    if type(item) is not dict or set(item) != expected or item["schema"] != "RelationshipEvidence" or item["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported RelationshipEvidence contract")
    relationship_evidence(item["observer"], item["target"], item["evidence_id"], item["kind"], item["tick"], item["value"], item["uncertainty"], item["provenance"])
    return item


def pregnancy_or_incubation(pregnancy_id, species_id, carrier_id, other_parent_id, conception_step,
                            required_steps, resource_cost_per_step, conception_event_id):
    """Create a durable gestation/incubation contract."""
    fields = [(pregnancy_id, "pregnancy_id"), (species_id, "species_id"),
              (carrier_id, "carrier_id"), (other_parent_id, "other parent"),
              (conception_event_id, "conception event")]
    for value, label in fields: _event_id(value) if label.endswith("event") else _id(value, label)
    if carrier_id == other_parent_id:
        raise ValueError("Sexual pregnancy needs distinct parents")
    _nonnegative_int(conception_step, "conception step"); _nonnegative_int(required_steps, "required gestation")
    if required_steps < 1:
        raise ValueError("Gestation must take elapsed biological time")
    if type(resource_cost_per_step) is not dict or not resource_cost_per_step:
        raise ValueError("Gestation needs resource costs")
    costs = {_id(k, "resource"): _finite(v, "resource cost", 0.0) for k, v in resource_cost_per_step.items()}
    result = {"schema": "PregnancyOrIncubation", "version": SCHEMA_VERSION,
              "pregnancy_id": pregnancy_id, "species_id": species_id,
              "carrier_id": carrier_id, "other_parent_id": other_parent_id,
              "conception_step": conception_step, "elapsed_steps": 0,
              "required_steps": required_steps, "resource_cost_per_step": costs,
              "resource_spent": {resource: 0.0 for resource in costs},
              "conception_event_id": conception_event_id, "last_advanced_step": None,
              "status": "active", "birth_event_id": None, "birth_applied": False}
    validate_pregnancy(result)
    return result


def validate_pregnancy(item):
    expected = {"schema", "version", "pregnancy_id", "species_id", "carrier_id",
                "other_parent_id", "conception_step", "elapsed_steps", "required_steps",
                "resource_cost_per_step", "resource_spent", "conception_event_id",
                "last_advanced_step", "status", "birth_event_id", "birth_applied"}
    if type(item) is not dict or set(item) != expected or item["schema"] != "PregnancyOrIncubation" or item["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported PregnancyOrIncubation contract")
    _id(item["pregnancy_id"], "pregnancy_id"); _id(item["species_id"], "species_id")
    _id(item["carrier_id"], "carrier_id"); _id(item["other_parent_id"], "other parent")
    if item["carrier_id"] == item["other_parent_id"]: raise ValueError("Pregnancy parents must differ")
    _nonnegative_int(item["conception_step"], "conception step"); _nonnegative_int(item["elapsed_steps"], "elapsed steps")
    _nonnegative_int(item["required_steps"], "required steps")
    if item["required_steps"] < 1 or item["elapsed_steps"] > item["required_steps"]:
        raise ValueError("Invalid pregnancy elapsed time")
    if type(item["resource_cost_per_step"]) is not dict or set(item["resource_cost_per_step"]) != set(item["resource_spent"]):
        raise ValueError("Invalid pregnancy resource accounting")
    for resource, amount in item["resource_cost_per_step"].items():
        _id(resource, "resource"); _finite(amount, "resource cost", 0.0); _finite(item["resource_spent"][resource], "resource spent", 0.0)
    _event_id(item["conception_event_id"])
    if item["last_advanced_step"] is not None: _nonnegative_int(item["last_advanced_step"], "last advanced step")
    if item["status"] not in {"active", "completed", "failed_resource_shortage"}:
        raise ValueError("Invalid pregnancy status")
    if item["birth_event_id"] is not None: _event_id(item["birth_event_id"])
    if type(item["birth_applied"]) is not bool or (item["birth_applied"] and item["birth_event_id"] is None):
        raise ValueError("Invalid birth application state")
    return item


def care_commitment(commitment_id, caregiver_id, dependent_id, resource, amount_per_step, accepted=True, start_step=0, duration_steps=1):
    """Create explicit caregiver/resource accounting metadata."""
    _id(commitment_id, "care commitment"); _id(caregiver_id, "caregiver"); _id(dependent_id, "dependent")
    if caregiver_id == dependent_id: raise ValueError("Caregiver and dependent must differ")
    _id(resource, "care resource"); _finite(amount_per_step, "care amount", 0.0)
    _nonnegative_int(start_step, "care start"); _nonnegative_int(duration_steps, "care duration")
    if duration_steps < 1 or type(accepted) is not bool: raise ValueError("Invalid care commitment")
    result = {"schema": "CareCommitment", "version": SCHEMA_VERSION,
              "commitment_id": commitment_id, "caregiver_id": caregiver_id,
              "dependent_id": dependent_id, "resource": resource,
              "amount_per_step": float(amount_per_step), "accepted": accepted,
              "start_step": start_step, "duration_steps": duration_steps,
              "applied_steps": [], "total_spent": 0.0, "status": "active" if accepted else "declined"}
    validate_care_commitment(result)
    return result


def validate_care_commitment(item):
    expected = {"schema", "version", "commitment_id", "caregiver_id", "dependent_id",
                "resource", "amount_per_step", "accepted", "start_step", "duration_steps",
                "applied_steps", "total_spent", "status"}
    if type(item) is not dict or set(item) != expected or item["schema"] != "CareCommitment" or item["version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported CareCommitment contract")
    _id(item["commitment_id"], "care commitment"); _id(item["caregiver_id"], "caregiver"); _id(item["dependent_id"], "dependent")
    if item["caregiver_id"] == item["dependent_id"]: raise ValueError("Caregiver and dependent must differ")
    _id(item["resource"], "care resource"); _finite(item["amount_per_step"], "care amount", 0.0)
    if type(item["accepted"]) is not bool: raise ValueError("Invalid care acceptance")
    _nonnegative_int(item["start_step"], "care start"); _nonnegative_int(item["duration_steps"], "care duration")
    if item["duration_steps"] < 1 or type(item["applied_steps"]) is not list or len(item["applied_steps"]) != len(set(item["applied_steps"])):
        raise ValueError("Invalid care applied steps")
    for step in item["applied_steps"]: _nonnegative_int(step, "care applied step")
    _finite(item["total_spent"], "care total", 0.0)
    if item["status"] not in {"active", "completed", "declined", "resource_shortage"}: raise ValueError("Invalid care status")
    return item


def _stage(contract, age):
    matching = [stage for stage in contract["stages"] if stage["min_age_steps"] <= age and (stage["max_age_steps"] is None or age <= stage["max_age_steps"])]
    if matching: return max(matching, key=lambda stage: stage["min_age_steps"])["stage_id"]
    return contract["stages"][-1]["stage_id"]


def _profile(contract, profile_id):
    return next((profile for profile in contract["reproductive_profiles"] if profile["profile_id"] == profile_id), None)


def _mature(state, person):
    contract = state["species"][person["species_id"]]
    stage = next(stage for stage in contract["stages"] if stage["stage_id"] == person["stage_id"])
    profile = _profile(contract, person["reproductive_profile_id"])
    if profile is None:
        return False
    maturity = next(stage for stage in contract["stages"] if stage["stage_id"] == profile["maturity_stage"])
    return bool(stage["can_reproduce"] and person["age_steps"] >= maturity["min_age_steps"] and person["alive"])


def _individual(person):
    _reject_forbidden(person, "individual")
    expected = {"id", "species_id", "age_steps", "stage_id", "biological_role", "gender_identity",
                "reproductive_profile_id", "alive", "traits", "resources", "knowledge", "lexicon", "relationship_ids"}
    if type(person) is not dict or not set(person).issubset(expected) or not {"id", "species_id", "age_steps", "biological_role", "gender_identity", "reproductive_profile_id", "alive", "traits", "resources"}.issubset(person):
        raise ValueError("Invalid lifecycle individual")
    result = deepcopy(person)
    _id(result["id"], "individual id"); _id(result["species_id"], "species id"); _nonnegative_int(result["age_steps"], "age")
    if result["biological_role"] not in BIOLOGICAL_ROLES: raise ValueError("Invalid biological role")
    if result["gender_identity"] not in IDENTITY_VALUES: raise ValueError("Invalid gender identity")
    _id(result["reproductive_profile_id"], "reproductive profile")
    if type(result["alive"]) is not bool: raise ValueError("Invalid life status")
    result["traits"] = _bounded_traits(result["traits"])
    if type(result["resources"]) is not dict: raise ValueError("Invalid individual resources")
    for resource, amount in result["resources"].items(): _id(resource, "resource"); _finite(amount, "resource amount", 0.0)
    result.setdefault("stage_id", "")
    result.setdefault("knowledge", [])
    result.setdefault("lexicon", [])
    result.setdefault("relationship_ids", [])
    if type(result["knowledge"]) is not list or type(result["lexicon"]) is not list or type(result["relationship_ids"]) is not list:
        raise ValueError("Individual developmental fields must be JSON lists")
    return result


def initial_state(run_id="lifecycle-run-1"):
    _id(run_id, "run_id")
    return {"schema": "LifecycleState", "version": SCHEMA_VERSION, "rule": RULE,
            "run_id": run_id, "clock_step": 0, "species": {}, "individuals": {},
            "relationships": {}, "partnership_invitations": {}, "partnerships": {},
            "pregnancies": {}, "lineages": {}, "care_commitments": {},
            "birth_events": {}, "applied_events": [], "conceptions_by_step": {}}


def validate_state(state):
    expected = {"schema", "version", "rule", "run_id", "clock_step", "species", "individuals",
                "relationships", "partnership_invitations", "partnerships", "pregnancies",
                "lineages", "care_commitments", "birth_events", "applied_events", "conceptions_by_step"}
    if type(state) is not dict or set(state) != expected or state["schema"] != "LifecycleState" or state["version"] != SCHEMA_VERSION or state["rule"] != RULE:
        raise ValueError("Unsupported LifecycleState schema")
    _id(state["run_id"], "run_id"); _nonnegative_int(state["clock_step"], "clock step")
    if type(state["species"]) is not dict or type(state["individuals"]) is not dict or len(state["individuals"]) > MAX_INDIVIDUALS:
        raise ValueError("Invalid lifecycle population")
    for species_id, contract in state["species"].items():
        if species_id != contract.get("species_id"): raise ValueError("Species identity mismatch")
        validate_species_lifecycle(contract)
    for ident, person in state["individuals"].items():
        if ident != person.get("id"): raise ValueError("Individual identity mismatch")
        canonical = _individual(person)
        if canonical != person: raise ValueError("Non-canonical individual")
        if person["species_id"] not in state["species"]: raise ValueError("Individual has unknown species")
        contract = state["species"][person["species_id"]]
        if person["stage_id"] != _stage(contract, person["age_steps"]): raise ValueError("Individual age stage mismatch")
        profile = _profile(contract, person["reproductive_profile_id"])
        if profile is None or profile["biological_role"] != person["biological_role"]: raise ValueError("Individual role/profile mismatch")
    for key, rel in state["relationships"].items():
        validate_relationship_evidence(rel["last_evidence"]) if rel.get("last_evidence") else None
        if key != f"{rel['observer']}->{rel['target']}": raise ValueError("Relationship identity mismatch")
    for item in state["pregnancies"].values(): validate_pregnancy(item)
    for item in state["lineages"].values(): validate_lineage(item)
    for item in state["care_commitments"].values(): validate_care_commitment(item)
    for item in state["birth_events"].values():
        if type(item) is not dict or set(item) != {"birth_event_id", "pregnancy_id", "child_id", "applied_once"} or item["applied_once"] is not True:
            raise ValueError("Invalid birth event ledger")
        _event_id(item["birth_event_id"]); _id(item["pregnancy_id"], "pregnancy_id"); _id(item["child_id"], "child_id")
    return state


def register_species(state, contract):
    validate_state(state); validate_species_lifecycle(contract)
    if contract["species_id"] in state["species"] and state["species"][contract["species_id"]] != contract:
        raise ValueError("Species lifecycle replacement is not allowed")
    state["species"][contract["species_id"]] = deepcopy(contract)
    return deepcopy(contract)


def add_individual(state, person):
    validate_state(state)
    person = _individual(person)
    if person["id"] in state["individuals"]: raise ValueError("Individual already exists")
    contract = state["species"].get(person["species_id"])
    if contract is None: raise ValueError("Register the species lifecycle first")
    profile = _profile(contract, person["reproductive_profile_id"])
    if profile is None or profile["biological_role"] != person["biological_role"]: raise ValueError("Invalid role/profile pairing")
    expected_stage = _stage(contract, person["age_steps"])
    if person.get("stage_id") not in (None, "", expected_stage):
        raise ValueError("Individual age stage does not match declared age")
    person["stage_id"] = expected_stage
    state["individuals"][person["id"]] = person
    validate_state(state)
    return deepcopy(person)


def record_relationship(state, evidence):
    validate_state(state); validate_relationship_evidence(evidence)
    if evidence["observer"] not in state["individuals"] or evidence["target"] not in state["individuals"]:
        raise ValueError("Relationship references unknown individual")
    key = f"{evidence['observer']}->{evidence['target']}"
    rel = state["relationships"].setdefault(key, {
        "schema": "DirectionalRelationship", "version": SCHEMA_VERSION,
        "observer": evidence["observer"], "target": evidence["target"],
        "familiarity": 0.0, "trust": 0.0, "affection": 0.0, "attraction": 0.0,
        "attachment": 0.0, "satisfaction": 0.0, "expectations": {}, "evidence": [], "last_evidence": None,
    })
    if any(item["evidence_id"] == evidence["evidence_id"] for item in rel["evidence"]): return deepcopy(rel)
    if len(rel["evidence"]) >= MAX_EVIDENCE: rel["evidence"] = rel["evidence"][1:]
    rel["evidence"].append(deepcopy(evidence)); rel["last_evidence"] = deepcopy(evidence)
    key_name = evidence["kind"] if evidence["kind"] in {"familiarity", "trust", "affection", "attraction", "attachment"} else None
    if key_name:
        rel[key_name] = max(-1.0, min(1.0, rel[key_name] + evidence["value"] * (1.0 - evidence["uncertainty"])))
    elif evidence["kind"] in {"shared_activity", "reliable_help", "responsiveness", "safety"}:
        rel["familiarity"] = min(1.0, rel["familiarity"] + .1)
        rel["trust"] = max(-1.0, min(1.0, rel["trust"] + evidence["value"] * .1))
    if evidence["kind"] == "invitation_declined": rel["satisfaction"] = max(-1.0, rel["satisfaction"] - .1)
    validate_state(state)
    return deepcopy(rel)


def propose_partnership(state, proposer, target, invitation_id, step):
    validate_state(state); proposer, target = _id(proposer, "proposer"), _id(target, "target"); _event_id(invitation_id); _nonnegative_int(step, "partnership step")
    if proposer == target or proposer not in state["individuals"] or target not in state["individuals"]: raise ValueError("Invalid partnership participants")
    if not _mature(state, state["individuals"][proposer]) or not _mature(state, state["individuals"][target]): raise ValueError("Partnership requires mature adults")
    if invitation_id in state["partnership_invitations"]: raise ValueError("Invitation identity already used")
    item = {"invitation_id": invitation_id, "proposer": proposer, "target": target, "step": step, "decisions": {proposer: None, target: None}, "status": "pending"}
    state["partnership_invitations"][invitation_id] = item
    return {"kind": "partnership_invitation_proposal", "invitation_id": invitation_id, "proposer": proposer, "target": target, "execution": "external"}


def decide_partnership(state, invitation_id, actor, accepted):
    validate_state(state); _event_id(invitation_id); _id(actor, "partnership actor")
    if type(accepted) is not bool: raise ValueError("Partnership decision must be boolean")
    invitation = state["partnership_invitations"].get(invitation_id)
    if invitation is None or actor not in invitation["decisions"]: raise ValueError("Unknown partnership invitation or actor")
    if invitation["status"] != "pending": return deepcopy(invitation)
    invitation["decisions"][actor] = accepted
    if not accepted:
        invitation["status"] = "declined"
        record_relationship(state, relationship_evidence(actor, invitation["proposer"] if actor == invitation["target"] else invitation["target"], "rel:" + invitation_id + ":declined", "invitation_declined", invitation["step"], -1.0, 0.0))
    elif invitation["decisions"][invitation["proposer"]] is True and invitation["decisions"][invitation["target"]] is True:
        invitation["status"] = "active"
        partnership = {"partnership_id": invitation_id, "participants": sorted([invitation["proposer"], invitation["target"]]), "accepted_decisions": deepcopy(invitation["decisions"]), "status": "active"}
        state["partnerships"][invitation_id] = partnership
    validate_state(state)
    return deepcopy(invitation)


def propose_conception(state, parent_a, parent_b, context):
    """Return a conception proposal; this function never starts a pregnancy."""
    validate_state(state); parent_a, parent_b = _id(parent_a, "parent a"), _id(parent_b, "parent b")
    if parent_a == parent_b or parent_a not in state["individuals"] or parent_b not in state["individuals"]: raise ValueError("Invalid conception pair")
    if type(context) is not dict or set(context) != {"step", "proximity", "current_intentions", "conditions", "roll"}: raise ValueError("Conception requires strict current conditions")
    _reject_forbidden(context, "conception context"); _nonnegative_int(context["step"], "conception step"); _finite(context["proximity"], "proximity", 0.0)
    if context["proximity"] > 1.5: raise ValueError("Conception pair is not in required proximity")
    intentions = context["current_intentions"]
    if type(intentions) is not dict or intentions != {parent_a: True, parent_b: True}: raise ValueError("Both current reproductive intentions are required")
    conditions = context["conditions"]
    if type(conditions) is not dict or set(conditions) != {parent_a, parent_b} or any(type(conditions[p]) is not dict or conditions[p].get("ready") is not True or conditions[p].get("available") is not True for p in (parent_a, parent_b)): raise ValueError("Feasible bodily conditions are required")
    _finite(context["roll"], "conception roll", 0.0, 1.0)
    a, b = state["individuals"][parent_a], state["individuals"][parent_b]
    if not _mature(state, a) or not _mature(state, b): raise ValueError("Conception requires mature adults")
    pa, pb = _profile(state["species"][a["species_id"]], a["reproductive_profile_id"]), _profile(state["species"][b["species_id"]], b["reproductive_profile_id"])
    if pa is None or pb is None:
        raise ValueError("Biologically incompatible reproductive profiles")
    if a["species_id"] != b["species_id"] or b["biological_role"] not in pa["compatible_roles"] or a["biological_role"] not in pb["compatible_roles"]: raise ValueError("Biologically incompatible reproductive profiles")
    carrier = parent_a if pa["biological_role"] == "female" else parent_b if pb["biological_role"] == "female" else parent_a
    carrier_profile = pa if carrier == parent_a else pb
    key = f"{carrier}:{context['step']}"
    if key in state["conceptions_by_step"] or any(item["carrier_id"] == carrier and item["status"] == "active" for item in state["pregnancies"].values()):
        raise ValueError("At most one active pregnancy per carrier and conception step")
    probability = carrier_profile["conception_probability"]
    return {"kind": "conception_proposal", "parent_ids": [parent_a, parent_b], "carrier_id": carrier,
            "step": context["step"], "probability": probability, "roll": context["roll"],
            "eligible": context["roll"] < probability, "execution": "external"}


def apply_conception(state, proposal, event_id):
    """Apply one explicit external conception result to a copied state."""
    validate_state(state); _event_id(event_id)
    if type(proposal) is not dict or proposal.get("kind") != "conception_proposal" or proposal.get("execution") != "external" or proposal.get("eligible") is not True: raise ValueError("Conception proposal is not eligible")
    parent_a, parent_b = proposal["parent_ids"]
    if event_id in state["applied_events"]: return deepcopy(state["pregnancies"].get("pregnancy:" + event_id))
    context = {"step": proposal["step"], "proximity": 0.0, "current_intentions": {parent_a: True, parent_b: True}, "conditions": {parent_a: {"ready": True, "available": True}, parent_b: {"ready": True, "available": True}}, "roll": proposal["roll"]}
    fresh = propose_conception(state, parent_a, parent_b, context)
    if fresh != proposal: raise ValueError("Conception proposal no longer matches current state")
    a, b = state["individuals"][parent_a], state["individuals"][parent_b]
    carrier = proposal["carrier_id"]; profile = _profile(state["species"][a["species_id"]], a["reproductive_profile_id"] if carrier == parent_a else b["reproductive_profile_id"])
    if profile is None:
        raise ValueError("Conception carrier profile is missing")
    pregnancy_id = "pregnancy:" + event_id
    pregnancy = pregnancy_or_incubation(pregnancy_id, a["species_id"], carrier, parent_b if carrier == parent_a else parent_a, proposal["step"], profile["gestation_steps"], profile["resource_cost_per_step"], event_id)
    state["pregnancies"][pregnancy_id] = pregnancy; state["conceptions_by_step"][f"{carrier}:{proposal['step']}"] = pregnancy_id; state["applied_events"].append(event_id)
    validate_state(state)
    return deepcopy(pregnancy)


def advance_time(state, elapsed_steps=1, current_step=None):
    """Advance gestation and age, applying each biological step once."""
    validate_state(state); _nonnegative_int(elapsed_steps, "elapsed steps")
    if current_step is None: current_step = state["clock_step"] + elapsed_steps
    _nonnegative_int(current_step, "current step")
    if current_step < state["clock_step"]: raise ValueError("Lifecycle clock cannot move backward")
    events = []
    for step in range(state["clock_step"] + 1, current_step + 1):
        for person in state["individuals"].values():
            if person["alive"]:
                person["age_steps"] += 1
                person["stage_id"] = _stage(state["species"][person["species_id"]], person["age_steps"])
        for pregnancy in state["pregnancies"].values():
            if pregnancy["status"] != "active" or pregnancy["last_advanced_step"] == step: continue
            carrier = state["individuals"].get(pregnancy["carrier_id"])
            if carrier is None or not carrier["alive"]:
                pregnancy["status"] = "failed_resource_shortage"; continue
            if any(float(carrier["resources"].get(resource, 0.0)) < amount for resource, amount in pregnancy["resource_cost_per_step"].items()):
                pregnancy["status"] = "failed_resource_shortage"; pregnancy["last_advanced_step"] = step; events.append({"kind": "gestation_failed", "pregnancy_id": pregnancy["pregnancy_id"], "step": step}); continue
            for resource, amount in pregnancy["resource_cost_per_step"].items():
                carrier["resources"][resource] = float(carrier["resources"].get(resource, 0.0)) - amount; pregnancy["resource_spent"][resource] += amount
            pregnancy["elapsed_steps"] += 1; pregnancy["last_advanced_step"] = step
            events.append({"kind": "gestation_step", "pregnancy_id": pregnancy["pregnancy_id"], "step": step})
            if pregnancy["elapsed_steps"] >= pregnancy["required_steps"] and not pregnancy["birth_applied"]:
                event_id = "birth:" + pregnancy["pregnancy_id"]
                child_id = "child-" + hashlib.sha256(pregnancy["pregnancy_id"].encode()).hexdigest()[:16]
                if event_id not in state["birth_events"]:
                    _create_birth(state, pregnancy, event_id, child_id)
                    events.append({"kind": "birth", "birth_event_id": event_id, "child_id": child_id})
    state["clock_step"] = current_step
    validate_state(state)
    return events


def _create_birth(state, pregnancy, birth_event_id, child_id):
    if birth_event_id in state["birth_events"]: return state["individuals"].get(child_id)
    carrier, other = state["individuals"][pregnancy["carrier_id"]], state["individuals"][pregnancy["other_parent_id"]]
    seed = int(hashlib.sha256(birth_event_id.encode()).hexdigest()[:16], 16)
    traits, mutations = inherit_traits(carrier["traits"], other["traits"], seed)
    contract = state["species"][pregnancy["species_id"]]; newborn_profile = next(profile for profile in contract["reproductive_profiles"] if profile["biological_role"] in {"none", "asexual", "female", "male", "dual"})
    child = {"id": child_id, "species_id": pregnancy["species_id"], "age_steps": 0,
             "stage_id": _stage(contract, 0), "biological_role": newborn_profile["biological_role"],
             "gender_identity": "unassigned", "reproductive_profile_id": newborn_profile["profile_id"], "alive": True,
             "traits": traits, "resources": {}, "knowledge": [], "lexicon": [], "relationship_ids": []}
    state["individuals"][child_id] = child
    state["lineages"][child_id] = lineage(child_id, [carrier["id"], other["id"]], traits, mutations, birth_event_id)
    state["birth_events"][birth_event_id] = {"birth_event_id": birth_event_id, "pregnancy_id": pregnancy["pregnancy_id"], "child_id": child_id, "applied_once": True}
    pregnancy["status"] = "completed"; pregnancy["birth_event_id"] = birth_event_id; pregnancy["birth_applied"] = True
    return child


def inherit_traits(parent_a, parent_b, seed, mutation_rate=0.08):
    """Return bounded recombination and bounded per-trait mutation."""
    a, b = _bounded_traits(parent_a, "parent traits"), _bounded_traits(parent_b, "parent traits")
    _nonnegative_int(seed, "inheritance seed"); _finite(mutation_rate, "mutation rate", 0.0, 0.25)
    rng = random.Random(seed); traits = {}; mutations = {}
    for key, (low, high) in TRAIT_RANGES.items():
        base = (a[key] + b[key]) / 2.0 if rng.random() < .5 else (a[key] if rng.random() < .5 else b[key])
        mutation = (rng.random() * 2.0 - 1.0) * mutation_rate if rng.random() < mutation_rate else 0.0
        mutations[key] = round(mutation, 6); traits[key] = round(max(low, min(high, base + mutation)), 6)
    return traits, mutations


def propose_care(state, caregiver_id, dependent_id, resource, amount_per_step, start_step, duration_steps, commitment_id):
    validate_state(state)
    for ident in (caregiver_id, dependent_id):
        if ident not in state["individuals"]: raise ValueError("Unknown care participant")
    return {"kind": "care_commitment_proposal", "commitment": care_commitment(commitment_id, caregiver_id, dependent_id, resource, amount_per_step, False, start_step, duration_steps), "execution": "external"}


def accept_care(state, proposal, accepted):
    validate_state(state)
    if type(proposal) is not dict or proposal.get("kind") != "care_commitment_proposal" or proposal.get("execution") != "external" or type(accepted) is not bool: raise ValueError("Invalid care proposal")
    item = deepcopy(proposal["commitment"]); item["accepted"] = accepted; item["status"] = "active" if accepted else "declined"
    prior=state['care_commitments'].get(item['commitment_id'])
    if prior is not None:
        immutable=('caregiver_id','dependent_id','resource','amount_per_step','start_step','duration_steps','accepted')
        if any(prior[key]!=item[key] for key in immutable):raise ValueError('Conflicting care commitment retry')
        return deepcopy(prior)
    validate_care_commitment(item); state["care_commitments"][item["commitment_id"]] = item; validate_state(state)
    return deepcopy(item)


def apply_care(state, commitment_id, step):
    validate_state(state); _id(commitment_id, "care commitment"); _nonnegative_int(step, "care step")
    item = state["care_commitments"].get(commitment_id)
    if item is None: raise ValueError("Unknown care commitment")
    if item["status"] != "active" or step < item["start_step"] or step >= item["start_step"] + item["duration_steps"]: return {"changed": False, "reason": item["status"]}
    if step in item["applied_steps"]: return {"changed": False, "reason": "idempotent_retry", "spent": 0.0}
    caregiver = state["individuals"][item["caregiver_id"]]; dependent = state["individuals"][item["dependent_id"]]
    available = float(caregiver["resources"].get(item["resource"], 0.0))
    if available < item["amount_per_step"]:
        item["status"] = "resource_shortage"; validate_state(state); return {"changed": False, "reason": "resource_shortage", "spent": 0.0}
    caregiver["resources"][item["resource"]] = available - item["amount_per_step"]
    dependent["resources"][item["resource"]] = float(dependent["resources"].get(item["resource"], 0.0)) + item["amount_per_step"]
    item["applied_steps"].append(step); item["total_spent"] += item["amount_per_step"]
    if len(item["applied_steps"]) >= item["duration_steps"]: item["status"] = "completed"
    validate_state(state); return {"changed": True, "spent": item["amount_per_step"], "step": step}


def dumps(state):
    validate_state(state)
    return json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def loads(text):
    if type(text) is not str: raise ValueError("Lifecycle JSON must be text")
    state = json.loads(text)
    validate_state(state)
    return state


def copy_restart(state):
    """Simulate a save/resume boundary without sharing mutable objects."""
    return loads(dumps(state))


# Explicit constructor aliases make the contract names easy to discover while
# retaining the dictionary-based conventions used by the existing sidecars.
from .foundation_transactions import rollback_on_error
for _name in ('register_species','add_individual','record_relationship',
              'propose_partnership','decide_partnership','apply_conception',
              'advance_time','accept_care','apply_care'):
    globals()[_name] = rollback_on_error(globals()[_name])

make_life_stage = life_stage
make_reproductive_profile = reproductive_profile
make_species_lifecycle = species_lifecycle
make_lineage = lineage
make_relationship_evidence = relationship_evidence
make_pregnancy_or_incubation = pregnancy_or_incubation
make_care_commitment = care_commitment


__all__ = [
    "RULE", "SCHEMA_VERSION", "IDENTITY_VALUES", "BIOLOGICAL_ROLES", "TRAIT_RANGES",
    "life_stage", "validate_life_stage", "reproductive_profile", "validate_reproductive_profile",
    "species_lifecycle", "validate_species_lifecycle", "lineage", "validate_lineage",
    "relationship_evidence", "validate_relationship_evidence", "pregnancy_or_incubation",
    "validate_pregnancy", "care_commitment", "validate_care_commitment", "initial_state",
    "validate_state", "register_species", "add_individual", "record_relationship",
    "propose_partnership", "decide_partnership", "propose_conception", "apply_conception",
    "advance_time", "inherit_traits", "propose_care", "accept_care", "apply_care",
    "dumps", "loads", "copy_restart",
    "make_life_stage", "make_reproductive_profile", "make_species_lifecycle",
    "make_lineage", "make_relationship_evidence", "make_pregnancy_or_incubation",
    "make_care_commitment",
]
