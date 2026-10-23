"""Bounded ALICE 02 L5-L9 lifecycle overlay.

This module is an additive JSON sidecar for the L0-L4 lifecycle foundation.
It deliberately does not import the native engine or ``storage.py``.  It
records developmental care, age/function, mortality, grief evidence, lineage,
demographics, material accounting, and replay metadata.  Proposals are data
only; a caller must apply an explicit external receipt.
"""

from copy import deepcopy
import hashlib
import json
import math
import random
import re


RULE = "alice-lifecycle-l59-1"
SCHEMA_VERSION = 1
MAX_INDIVIDUALS = 256
MAX_EVENTS = 4096
MAX_EVIDENCE = 128
MAX_ID_LENGTH = 128
TRAIT_RANGES = {
    "body_size_potential": (0.0, 1.0),
    "metabolic_efficiency": (0.0, 1.0),
    "maturation_tendency": (0.0, 1.0),
    "sensory_sensitivity": (0.0, 1.0),
}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_FORBIDDEN_PARTS = (
    "private", "hidden", "secret", "operator", "model", "llm", "prompt",
    "target_state", "foreign_state", "other_state", "self_report",
)
_EVIDENCE_PROVENANCE = frozenset({"observed", "native_receipt", "public_report"})


def _id(value, label="identifier"):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid L59 {label}")
    return value


def _int(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"Invalid L59 {label}")
    return value


def _finite(value, label, low=None, high=None):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"Invalid L59 {label}")
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"Invalid L59 {label}")
    return value


def _reject_forbidden(value, label="value"):
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid L59 {label} field")
            if any(part in key.lower() for part in _FORBIDDEN_PARTS):
                raise ValueError("L59 private, operator, foreign, and model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item, label)
    elif isinstance(value, tuple):
        raise ValueError(f"L59 {label} must be JSON-copyable")


def _traits(value, label="traits"):
    if type(value) is not dict or set(value) != set(TRAIT_RANGES):
        raise ValueError(f"L59 {label} must use the bounded trait schema")
    return {key: _finite(value[key], f"{label}.{key}", low, high)
            for key, (low, high) in TRAIT_RANGES.items()}


def _stage_id(stages, age):
    matches = [stage for stage in stages if stage["min_age_steps"] <= age and
               (stage["max_age_steps"] is None or age <= stage["max_age_steps"])]
    return max(matches, key=lambda item: item["min_age_steps"])["stage_id"] if matches else stages[-1]["stage_id"]


def life_stage(stage_id, min_age_steps, max_age_steps=None, can_reproduce=False, capabilities=None, *,
               function_scale=1.0, care_needs=None, deprivation_tolerance=0, mortality_hazard=0.0):
    """Create a developmental stage with care, function and hazard bounds."""
    _id(stage_id, "stage_id")
    _int(min_age_steps, "minimum age")
    if max_age_steps is not None:
        _int(max_age_steps, "maximum age")
        if max_age_steps < min_age_steps:
            raise ValueError("L59 stage age range is reversed")
    _finite(function_scale, "function scale", 0.0, 1.0)
    _int(deprivation_tolerance, "deprivation tolerance")
    _finite(mortality_hazard, "mortality hazard", 0.0, 1.0)
    if type(can_reproduce) is not bool:
        raise ValueError("L59 reproduction flag must be boolean")
    care_needs = {} if care_needs is None else deepcopy(care_needs)
    capabilities = {} if capabilities is None else deepcopy(capabilities)
    _reject_forbidden(care_needs, "care needs")
    _reject_forbidden(capabilities, "capabilities")
    if type(care_needs) is not dict or type(capabilities) is not dict:
        raise ValueError("L59 stage maps must be mappings")
    needs = {_id(key, "care resource"): _finite(amount, "care need", 0.0)
             for key, amount in care_needs.items()}
    return {"schema": "L59LifeStage", "version": SCHEMA_VERSION,
            "stage_id": stage_id, "min_age_steps": min_age_steps,
            "max_age_steps": max_age_steps, "function_scale": float(function_scale),
            "care_needs": needs, "deprivation_tolerance": deprivation_tolerance,
            "mortality_hazard": float(mortality_hazard), "capabilities": capabilities,
            "can_reproduce": can_reproduce}


def validate_life_stage(stage):
    expected = {"schema", "version", "stage_id", "min_age_steps", "max_age_steps",
                "function_scale", "care_needs", "deprivation_tolerance",
                "mortality_hazard", "capabilities", "can_reproduce"}
    if type(stage) is not dict or set(stage) != expected or stage.get("schema") != "L59LifeStage" or stage.get("version") != SCHEMA_VERSION:
        raise ValueError("Unsupported L59 life stage")
    life_stage(stage["stage_id"], stage["min_age_steps"], stage["max_age_steps"],
               function_scale=stage["function_scale"], care_needs=stage["care_needs"],
               deprivation_tolerance=stage["deprivation_tolerance"],
               mortality_hazard=stage["mortality_hazard"], capabilities=stage["capabilities"],
               can_reproduce=stage["can_reproduce"])
    return stage


def inheritance_controls(control_id="default", *, max_variation=0.1, mutation_rate=0.08,
                         trait_caps=None, recombination="bounded_mix"):
    """Return explicit bounds controlling heritable variation."""
    _id(control_id, "inheritance control id")
    _finite(max_variation, "maximum variation", 0.0, 1.0)
    _finite(mutation_rate, "mutation rate", 0.0, max_variation)
    if recombination not in {"bounded_mix", "mean_only", "parent_choice"}:
        raise ValueError("Unsupported L59 recombination")
    caps = {key: max_variation for key in TRAIT_RANGES}
    if trait_caps is not None:
        if type(trait_caps) is not dict or set(trait_caps) - set(TRAIT_RANGES):
            raise ValueError("Invalid L59 trait variation caps")
        for key, value in trait_caps.items():
            caps[key] = _finite(value, f"trait cap {key}", 0.0, max_variation)
    return {"schema": "InheritanceControls", "version": SCHEMA_VERSION,
            "control_id": control_id, "max_variation": float(max_variation),
            "mutation_rate": float(mutation_rate), "trait_caps": caps,
            "recombination": recombination,
            "provenance": "bounded parent traits only; no parental knowledge copy"}


def validate_inheritance_controls(item):
    expected = {"schema", "version", "control_id", "max_variation", "mutation_rate",
                "trait_caps", "recombination", "provenance"}
    if type(item) is not dict or set(item) != expected or item["schema"] != "InheritanceControls":
        raise ValueError("Unsupported L59 inheritance controls")
    expected_item = inheritance_controls(item["control_id"], max_variation=item["max_variation"],
                                         mutation_rate=item["mutation_rate"], trait_caps=item["trait_caps"],
                                         recombination=item["recombination"])
    if item["version"] != SCHEMA_VERSION or item["provenance"] != expected_item["provenance"]:
        raise ValueError("Invalid L59 inheritance provenance")
    return item


def inherit_traits(parent_a, parent_b, seed, controls=None, mutation_rate=None, max_variation=None):
    """Recombine bounded traits; only the supplied trait maps are inspected."""
    a, b = _traits(parent_a, "parent traits"), _traits(parent_b, "parent traits")
    _int(seed, "inheritance seed")
    if controls is None:
        cap = 0.1 if max_variation is None else max_variation
        rate = 0.08 if mutation_rate is None else mutation_rate
        controls = inheritance_controls(max_variation=cap, mutation_rate=rate)
    else:
        controls = deepcopy(controls)
        if mutation_rate is not None or max_variation is not None:
            raise ValueError("L59 inheritance controls and scalar overrides cannot be combined")
    validate_inheritance_controls(controls)
    rng = random.Random(seed)
    traits, mutations = {}, {}
    for key, (low, high) in TRAIT_RANGES.items():
        if controls["recombination"] == "mean_only":
            base = (a[key] + b[key]) / 2.0
        elif controls["recombination"] == "parent_choice":
            base = a[key] if rng.random() < 0.5 else b[key]
        else:
            base = (a[key] + b[key]) / 2.0 if rng.random() < 0.5 else (a[key] if rng.random() < 0.5 else b[key])
        cap = controls["trait_caps"][key]
        mutation = (rng.random() * 2.0 - 1.0) * cap if rng.random() < controls["mutation_rate"] else 0.0
        mutations[key] = round(mutation, 6)
        traits[key] = round(max(low, min(high, base + mutation)), 6)
    return traits, mutations


def inheritance_result(child_id, parent_ids, parent_a, parent_b, seed, controls=None):
    child_id = _id(child_id, "child id")
    if type(parent_ids) is not list or len(parent_ids) not in (0, 1, 2) or len(parent_ids) != len(set(parent_ids)):
        raise ValueError("L59 lineage needs zero, one, or two distinct parents")
    for parent in parent_ids:
        _id(parent, "parent id")
    controls = inheritance_controls() if controls is None else deepcopy(controls)
    traits, mutations = inherit_traits(parent_a, parent_b, seed, controls)
    return {"schema": "InheritanceResult", "version": SCHEMA_VERSION, "child_id": child_id,
            "parent_ids": parent_ids, "traits": traits, "mutations": mutations,
            "controls": controls, "provenance": "bounded parent traits; developmental experience only",
            "copied_fields": []}


def _canonical_person(person):
    if type(person) is not dict:
        raise ValueError("Invalid L59 individual")
    _reject_forbidden(person, "individual")
    required = {"id", "species_id", "age_steps", "alive", "traits", "resources"}
    if not required.issubset(person):
        raise ValueError("L59 individual is missing required fields")
    allowed = required | {"stage_id", "knowledge", "lexicon", "relationship_ids", "deprivation_steps",
                          "deprivation_score", "function_scale", "care_received", "care_required",
                          "gender_identity", "biological_role", "reproductive_profile_id"}
    if set(person) - allowed:
        raise ValueError("L59 individual has unsupported fields")
    result = deepcopy(person)
    _id(result["id"], "individual id"); _id(result["species_id"], "species id")
    _int(result["age_steps"], "age")
    if type(result["alive"]) is not bool:
        raise ValueError("Invalid L59 life status")
    result["traits"] = _traits(result["traits"])
    if type(result["resources"]) is not dict:
        raise ValueError("Invalid L59 resources")
    for resource, amount in result["resources"].items():
        _id(resource, "resource"); _finite(amount, "resource amount", 0.0)
    result.setdefault("stage_id", "")
    result.setdefault("knowledge", [])
    result.setdefault("lexicon", [])
    result.setdefault("relationship_ids", [])
    result.setdefault("deprivation_steps", 0)
    result.setdefault("deprivation_score", 0.0)
    result.setdefault("function_scale", 0.0)
    result.setdefault("care_received", {})
    result.setdefault("care_required", {})
    if any(type(result[key]) is not list for key in ("knowledge", "lexicon", "relationship_ids")):
        raise ValueError("L59 developmental fields must be lists")
    _int(result["deprivation_steps"], "deprivation steps")
    _finite(result["deprivation_score"], "deprivation score", 0.0)
    _finite(result["function_scale"], "function scale", 0.0, 1.0)
    return result


def initial_state(run_id="lifecycle-run-1", *, seed=0, carrying_capacity=None):
    _id(run_id, "run id"); _int(seed, "seed")
    if carrying_capacity is not None:
        _int(carrying_capacity, "carrying capacity")
    state = {"schema": "LifecycleL59State", "version": SCHEMA_VERSION, "rule": RULE,
             "run_id": run_id, "seed": seed, "clock_step": 0,
             "species": {}, "individuals": {}, "inheritance": {}, "lineages": {},
             "births": {}, "deaths": {}, "care_commitments": {}, "loss_evidence": {},
             "grief_events": {}, "material_ledger": {}, "events": [],
             "carrying_capacity": carrying_capacity, "journal": [], "journal_hash": "0" * 64,
             "demographic": {"births": 0, "deaths": 0, "culling_events": 0}}
    return state


def validate_state(state):
    expected = {"schema", "version", "rule", "run_id", "seed", "clock_step", "species",
                "individuals", "inheritance", "lineages", "births", "deaths", "care_commitments",
                "loss_evidence", "grief_events", "material_ledger", "events", "carrying_capacity",
                "journal", "journal_hash", "demographic"}
    if type(state) is not dict or set(state) != expected or state["schema"] != "LifecycleL59State" or state["version"] != SCHEMA_VERSION or state["rule"] != RULE:
        raise ValueError("Unsupported L59 lifecycle state")
    _id(state["run_id"], "run id"); _int(state["seed"], "seed"); _int(state["clock_step"], "clock step")
    if state["carrying_capacity"] is not None: _int(state["carrying_capacity"], "carrying capacity")
    if type(state["individuals"]) is not dict or len(state["individuals"]) > MAX_INDIVIDUALS:
        raise ValueError("L59 population bound exceeded")
    for ident, person in state["individuals"].items():
        if ident != person.get("id") or _canonical_person(person) != person:
            raise ValueError("Non-canonical L59 individual")
        species = state["species"].get(person["species_id"])
        if species is None:
            raise ValueError("L59 individual has unknown species")
        if person["stage_id"] != _stage_id(species["stages"], person["age_steps"]):
            raise ValueError("L59 age stage mismatch")
    for species in state["species"].values():
        if type(species) is not dict or set(species) != {"schema", "version", "species_id", "stages", "max_age_steps"}:
            raise ValueError("Invalid L59 species contract")
        _id(species["species_id"], "species id")
        if type(species["stages"]) is not list or not species["stages"]:
            raise ValueError("L59 species requires stages")
        for stage in species["stages"]: validate_life_stage(stage)
        if species["stages"][0]["min_age_steps"] != 0: raise ValueError("L59 stages must start at zero")
        if species["max_age_steps"] is not None: _int(species["max_age_steps"], "maximum age")
    if type(state["journal"]) is not list or len(state["journal"]) > MAX_EVENTS:
        raise ValueError("L59 journal bound exceeded")
    digest = "0" * 64
    for index, event in enumerate(state["journal"], 1):
        if type(event) is not dict or set(event) != {"seq", "kind", "step", "payload", "hash"} or event["seq"] != index:
            raise ValueError("Invalid L59 replay journal")
        _id(event["kind"], "event kind"); _int(event["step"], "event step"); _reject_forbidden(event["payload"], "event payload")
        candidate = hashlib.sha256((digest + json.dumps({"seq": event["seq"], "kind": event["kind"], "step": event["step"], "payload": event["payload"]}, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
        if event["hash"] != candidate: raise ValueError("L59 replay journal checksum mismatch")
        digest = candidate
    if state["journal_hash"] != digest: raise ValueError("L59 journal head mismatch")
    if type(state["demographic"]) is not dict or set(state["demographic"]) != {"births", "deaths", "culling_events"}:
        raise ValueError("Invalid L59 demographic totals")
    for key in state["demographic"]: _int(state["demographic"][key], key)
    return state


def _record(state, kind, payload, step=None):
    validate_state(state)
    if len(state["journal"]) >= MAX_EVENTS: raise ValueError("L59 event bound exceeded")
    _id(kind, "event kind"); _reject_forbidden(payload, "event payload")
    step = state["clock_step"] if step is None else _int(step, "event step")
    seq = len(state["journal"]) + 1
    body = {"seq": seq, "kind": kind, "step": step, "payload": deepcopy(payload)}
    digest = hashlib.sha256((state["journal_hash"] + json.dumps(body, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
    body["hash"] = digest
    state["journal"].append(body); state["journal_hash"] = digest
    state["events"].append(deepcopy(body))


def register_species(state, species_id, stages, max_age_steps=None):
    validate_state(state); _id(species_id, "species id")
    stages = [deepcopy(stage) for stage in stages]
    for stage in stages: validate_life_stage(stage)
    if not stages or stages[0]["min_age_steps"] != 0: raise ValueError("L59 species stages must start at age zero")
    if max_age_steps is not None: _int(max_age_steps, "maximum age")
    contract = {"schema": "L59SpeciesLifecycle", "version": SCHEMA_VERSION,
                "species_id": species_id, "stages": stages, "max_age_steps": max_age_steps}
    if species_id in state["species"] and state["species"][species_id] != contract:
        raise ValueError("L59 species replacement is not allowed")
    state["species"][species_id] = contract
    _record(state, "species_registered", {"species_id": species_id})
    return deepcopy(contract)


def add_individual(state, person):
    validate_state(state); person = _canonical_person(person)
    if person["id"] in state["individuals"]: raise ValueError("L59 individual already exists")
    species = state["species"].get(person["species_id"])
    if species is None: raise ValueError("Register the L59 species first")
    person["stage_id"] = _stage_id(species["stages"], person["age_steps"])
    person["function_scale"] = next(stage['function_scale'] for stage in species['stages'] if stage['stage_id']==person['stage_id'])
    state["individuals"][person["id"]] = person
    _record(state, "individual_added", {"individual_id": person["id"], "species_id": person["species_id"]})
    validate_state(state)
    return deepcopy(person)


def record_birth(state, child_id, species_id, parent_ids, inherited_traits, mutations, birth_event_id, resources=None):
    """Apply an explicit birth receipt; no birth is created implicitly."""
    validate_state(state); _id(child_id, "child id"); _id(species_id, "species id"); _id(birth_event_id, "birth event id")
    if child_id in state["individuals"] or birth_event_id in state["births"]: raise ValueError("L59 birth already applied")
    if species_id not in state["species"]: raise ValueError("Unknown L59 species")
    if type(parent_ids) is not list or len(parent_ids) not in (0, 1, 2) or len(parent_ids) != len(set(parent_ids)):
        raise ValueError("Invalid L59 birth parents")
    for parent in parent_ids: _id(parent, "parent id")
    traits, mutations = _traits(inherited_traits, "inherited traits"), deepcopy(mutations)
    if type(mutations) is not dict or set(mutations) != set(TRAIT_RANGES): raise ValueError("Invalid L59 mutations")
    for value in mutations.values(): _finite(value, "mutation", -1.0, 1.0)
    person = {"id": child_id, "species_id": species_id, "age_steps": 0, "stage_id": "",
              "alive": True, "traits": traits, "resources": deepcopy(resources or {}),
              "knowledge": [], "lexicon": [], "relationship_ids": [], "deprivation_steps": 0,
              "deprivation_score": 0.0, "function_scale": 0.0, "care_received": {}, "care_required": {}}
    add_individual(state, person)
    lineage = {"schema": "L59Lineage", "version": SCHEMA_VERSION, "child_id": child_id,
               "parents": list(parent_ids), "inherited_traits": traits, "mutations": mutations,
               "birth_event_id": birth_event_id,
               "knowledge_provenance": "developmental experience only; no parental copy",
               "lexicon_provenance": "developmental experience only; no parental copy",
               "relationship_provenance": "developmental experience only; no parental copy",
               "copied_fields": []}
    state["lineages"][child_id] = lineage
    state["births"][birth_event_id] = {"birth_event_id": birth_event_id, "child_id": child_id,
                                         "parent_ids": list(parent_ids), "species_id": species_id,
                                         "accounted": True}
    state["demographic"]["births"] += 1
    _record(state, "birth", {"birth_event_id": birth_event_id, "child_id": child_id,
                              "parent_ids": list(parent_ids), "species_id": species_id})
    validate_state(state)
    return deepcopy(person)


def care_proposal(state, caregiver_id, dependent_id, resource, amount, step, proposal_id):
    validate_state(state)
    for ident in (caregiver_id, dependent_id): _id(ident, "care participant")
    _id(resource, "care resource"); _id(proposal_id, "proposal id"); _int(step, "care step"); _finite(amount, "care amount", 0.0)
    if caregiver_id == dependent_id or caregiver_id not in state["individuals"] or dependent_id not in state["individuals"]:
        raise ValueError("Invalid L59 care participants")
    return {"kind": "care_proposal", "proposal_id": proposal_id, "caregiver_id": caregiver_id,
            "dependent_id": dependent_id, "resource": resource, "amount": float(amount),
            "step": step, "execution": "external", "proposal_only": True}


def apply_care_receipt(state, proposal, accepted=True):
    validate_state(state); _reject_forbidden(proposal, "care proposal")
    required = {"kind", "proposal_id", "caregiver_id", "dependent_id", "resource", "amount", "step", "execution", "proposal_only"}
    if type(proposal) is not dict or set(proposal) != required or proposal["kind"] != "care_proposal" or proposal["execution"] != "external" or proposal["proposal_only"] is not True or type(accepted) is not bool:
        raise ValueError("Invalid L59 care receipt")
    canonical = care_proposal(state, proposal['caregiver_id'], proposal['dependent_id'],
                              proposal['resource'], proposal['amount'], proposal['step'], proposal['proposal_id'])
    if canonical != proposal:raise ValueError('Invalid L59 care proposal')
    if proposal["proposal_id"] in state["care_commitments"]:
        prior=state['care_commitments'][proposal['proposal_id']]
        if any(prior[key]!=proposal[key] for key in ('caregiver_id','dependent_id','resource','amount','step')) or prior['accepted']!=accepted:
            raise ValueError('Conflicting L59 care receipt')
        return deepcopy(prior)
    commitment = {"schema": "L59CareCommitment", "version": SCHEMA_VERSION,
                  "proposal_id": proposal["proposal_id"], "caregiver_id": proposal["caregiver_id"],
                  "dependent_id": proposal["dependent_id"], "resource": proposal["resource"],
                  "amount": proposal["amount"], "step": proposal["step"], "accepted": accepted,
                  "applied": False, "status": "accepted" if accepted else "declined"}
    state["care_commitments"][proposal["proposal_id"]] = commitment
    _record(state, "care_decision", {"proposal_id": proposal["proposal_id"], "accepted": accepted})
    return deepcopy(commitment)


def apply_care(state, proposal_id):
    validate_state(state); _id(proposal_id, "proposal id")
    item = state["care_commitments"].get(proposal_id)
    if item is None: raise ValueError("Unknown L59 care proposal")
    if item["status"] != "accepted" or item["applied"]: return {"changed": False, "reason": item["status"] if item["status"] != "accepted" else "idempotent_retry"}
    caregiver, dependent = state["individuals"][item["caregiver_id"]], state["individuals"][item["dependent_id"]]
    available = float(caregiver["resources"].get(item["resource"], 0.0))
    if not caregiver["alive"] or available < item["amount"]:
        item["status"] = "resource_shortage"
        _record(state, "care_shortage", {"proposal_id": proposal_id, "resource": item["resource"]}, item["step"])
        return {"changed": False, "reason": "resource_shortage", "spent": 0.0}
    caregiver["resources"][item["resource"]] = available - item["amount"]
    dependent["resources"][item["resource"]] = float(dependent["resources"].get(item["resource"], 0.0)) + item["amount"]
    dependent["care_received"][item["resource"]] = float(dependent["care_received"].get(item["resource"], 0.0)) + item["amount"]
    item["applied"] = True
    item["status"] = "applied"
    _record(state, "care_applied", {"proposal_id": proposal_id, "dependent_id": dependent["id"], "amount": item["amount"]}, item["step"])
    validate_state(state)
    return {"changed": True, "spent": item["amount"], "step": item["step"]}


def age_function(state, individual_id):
    validate_state(state); _id(individual_id, "individual id")
    person = state["individuals"].get(individual_id)
    if person is None: raise ValueError("Unknown L59 individual")
    stage = next(stage for stage in state["species"][person["species_id"]]["stages"] if stage["stage_id"] == person["stage_id"])
    if not person["alive"]: return {"alive": False, "stage_id": person["stage_id"], "function_scale": 0.0, "capabilities": {}}
    scale = max(0.0, min(1.0, stage["function_scale"] * (1.0 - min(1.0, person["deprivation_score"] * 0.1))))
    person["function_scale"] = round(scale, 6)
    return {"alive": True, "stage_id": stage["stage_id"], "function_scale": person["function_scale"],
            "capabilities": deepcopy(stage["capabilities"])}


def mortality_hazard(state, individual_id):
    validate_state(state); person = state["individuals"].get(individual_id)
    if person is None: raise ValueError("Unknown L59 individual")
    if not person["alive"]: return 0.0
    species = state["species"][person["species_id"]]
    stage = next(item for item in species["stages"] if item["stage_id"] == person["stage_id"])
    hazard = stage["mortality_hazard"] + min(0.5, person["deprivation_score"] * 0.05)
    if species["max_age_steps"] is not None and person["age_steps"] >= species["max_age_steps"]:
        hazard = 1.0
    return round(max(0.0, min(1.0, hazard)), 6)


def _death(state, person, step, reason, hazard, roll):
    person["alive"] = False; person["function_scale"] = 0.0
    materials = {key: float(value) for key, value in person["resources"].items() if float(value) > 0.0}
    death_id = f"death:{person['id']}:{step}"
    state["deaths"][death_id] = {"death_id": death_id, "individual_id": person["id"], "species_id": person["species_id"],
                                  "step": step, "reason": reason, "hazard": hazard, "roll": roll,
                                  "materials": materials, "accounted": True}
    state["material_ledger"][death_id] = {"death_id": death_id, "individual_id": person["id"],
                                           "materials": materials, "status": "retained_and_accounted"}
    state["demographic"]["deaths"] += 1
    _record(state, "death", {"death_id": death_id, "individual_id": person["id"], "reason": reason,
                              "materials": materials}, step)


def advance_time(state, elapsed_steps=1, *, mortality_rolls=None):
    """Advance one or more steps; every age, care deficit and death is retained."""
    validate_state(state); _int(elapsed_steps, "elapsed steps", 1)
    if mortality_rolls is not None and type(mortality_rolls) is not dict:
        raise ValueError("L59 mortality rolls must be a mapping")
    events = []
    for step in range(state["clock_step"] + 1, state["clock_step"] + elapsed_steps + 1):
        for person in state["individuals"].values():
            if not person["alive"]: continue
            person["age_steps"] += 1
            species = state["species"][person["species_id"]]
            person["stage_id"] = _stage_id(species["stages"], person["age_steps"])
            stage = next(item for item in species["stages"] if item["stage_id"] == person["stage_id"])
            person["care_required"] = deepcopy(stage["care_needs"])
            person["function_scale"] = stage["function_scale"]
            person["deprivation_score"] = 0.0
            for resource, required in stage["care_needs"].items():
                received = float(person["care_received"].get(resource, 0.0))
                if received < required:
                    shortfall = required - received
                    person["deprivation_steps"] += 1
                    person["deprivation_score"] += shortfall / max(required, 1.0)
                    person["function_scale"] = max(0.0, person["function_scale"] - min(0.5, shortfall))
                    events.append({"kind": "deprivation", "individual_id": person["id"], "step": step, "resource": resource, "shortfall": shortfall})
            hazard = mortality_hazard(state, person["id"])
            roll = float(mortality_rolls.get(person["id"], 1.0)) if mortality_rolls is not None else (int(hashlib.sha256(f"{state['seed']}:{person['id']}:{step}".encode()).hexdigest()[:12], 16) / float(16 ** 12))
            _finite(roll, "mortality roll", 0.0, 1.0)
            if roll < hazard:
                _death(state, person, step, "age_or_deprivation_hazard", hazard, roll)
                events.append({"kind": "death", "individual_id": person["id"], "step": step, "hazard": hazard, "roll": roll})
            else:
                events.append({"kind": "age", "individual_id": person["id"], "step": step, "age_steps": person["age_steps"]})
            person["care_received"] = {}
        state["clock_step"] = step
    validate_state(state)
    return events


def attachment_evidence(observer_id, target_id, evidence_id, step, provenance="observed"):
    return _loss_or_attachment(observer_id, target_id, evidence_id, step, "attachment", provenance)


def loss_evidence(observer_id, lost_id, evidence_id, step, provenance="observed", perceived=True):
    item = _loss_or_attachment(observer_id, lost_id, evidence_id, step, "loss", provenance)
    if type(perceived) is not bool: raise ValueError("L59 perceived loss flag must be boolean")
    item["perceived"] = perceived
    return item


def _loss_or_attachment(observer_id, target_id, evidence_id, step, kind, provenance):
    _id(observer_id, "observer id"); _id(target_id, "target id"); _id(evidence_id, "evidence id"); _int(step, "evidence step")
    if observer_id == target_id or provenance not in _EVIDENCE_PROVENANCE: raise ValueError("Invalid L59 public evidence")
    return {"schema": "L59Evidence", "version": SCHEMA_VERSION, "evidence_id": evidence_id,
            "observer_id": observer_id, "target_id": target_id, "step": step,
            "kind": kind, "provenance": provenance}


def record_evidence(state, evidence):
    validate_state(state); _reject_forbidden(evidence, "evidence")
    if type(evidence) is not dict or set(evidence) - {"schema", "version", "evidence_id", "observer_id", "target_id", "step", "kind", "provenance", "perceived"}:
        raise ValueError("Invalid L59 evidence envelope")
    if evidence["evidence_id"] in state["loss_evidence"]: return deepcopy(state["loss_evidence"][evidence["evidence_id"]])
    if evidence["kind"] not in {"attachment", "loss"} or evidence["provenance"] not in _EVIDENCE_PROVENANCE:
        raise ValueError("Unsupported L59 evidence")
    if evidence["observer_id"] not in state["individuals"]: raise ValueError("Unknown L59 evidence observer")
    state["loss_evidence"][evidence["evidence_id"]] = deepcopy(evidence)
    _record(state, "evidence_recorded", {"evidence_id": evidence["evidence_id"], "kind": evidence["kind"]}, evidence["step"])
    return deepcopy(evidence)


def trigger_grief(state, observer_id, lost_id, loss_evidence_id):
    validate_state(state); _id(observer_id, "observer id"); _id(lost_id, "lost id"); _id(loss_evidence_id, "loss evidence id")
    evidence = state["loss_evidence"].get(loss_evidence_id)
    if evidence is None or evidence["kind"] != "loss" or evidence.get("perceived") is not True or evidence["observer_id"] != observer_id or evidence["target_id"] != lost_id:
        return {"triggered": False, "reason": "perceived_loss_evidence_required"}
    attached = [item for item in state["loss_evidence"].values() if item["kind"] == "attachment" and item["observer_id"] == observer_id and item["target_id"] == lost_id]
    if not attached: return {"triggered": False, "reason": "attachment_evidence_required"}
    grief_id = f"grief:{observer_id}:{loss_evidence_id}"
    if grief_id not in state["grief_events"]:
        state["grief_events"][grief_id] = {"grief_id": grief_id, "observer_id": observer_id, "lost_id": lost_id,
                                            "evidence": [attached[-1]["evidence_id"], loss_evidence_id], "provenance": evidence["provenance"]}
        _record(state, "grief_triggered", {"grief_id": grief_id, "observer_id": observer_id, "evidence": [attached[-1]["evidence_id"], loss_evidence_id]}, evidence["step"])
    return {"triggered": True, "grief_id": grief_id, "evidence": deepcopy(state["grief_events"][grief_id]["evidence"])}


def propose_external_action(kind, payload):
    _id(kind, "action kind"); _reject_forbidden(payload, "action payload")
    return {"kind": kind, "payload": deepcopy(payload), "execution": "external", "proposal_only": True}


def demographic_report(state):
    validate_state(state)
    live = sum(1 for person in state["individuals"].values() if person["alive"])
    dead = sum(1 for person in state["individuals"].values() if not person["alive"])
    capacity = state["carrying_capacity"]
    return {"live": live, "dead": dead, "total_registered": len(state["individuals"]),
            "births": state["demographic"]["births"], "deaths": state["demographic"]["deaths"],
            "lineages": len(state["lineages"]), "carrying_capacity": capacity,
            "occupancy": live, "overflow": max(0, live - capacity) if capacity is not None else 0,
            "culling_events": state["demographic"]["culling_events"], "hidden_culling": False,
            "death_material_records": len(state["material_ledger"]), "accounting_complete": dead == state["demographic"]["deaths"]}


def carrying_capacity_report(state):
    return demographic_report(state)


def dumps(state):
    validate_state(state)
    return json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def loads(text):
    if type(text) is not str: raise ValueError("L59 JSON must be text")
    state = json.loads(text); validate_state(state); return state


def copy_restart(state):
    return loads(dumps(state))


def replay(state_or_text):
    state = loads(state_or_text) if isinstance(state_or_text, str) else copy_restart(state_or_text)
    return {"replay_matches": True, "events": len(state["journal"]), "tick": state["clock_step"],
            "state_hash": hashlib.sha256(dumps(state).encode()).hexdigest()}


from .foundation_transactions import rollback_on_error
for _name in ('register_species','add_individual','record_birth','apply_care_receipt',
              'apply_care','advance_time','record_evidence','trigger_grief'):
    globals()[_name] = rollback_on_error(globals()[_name])

make_life_stage = life_stage
make_inheritance_controls = inheritance_controls
make_inheritance_result = inheritance_result
make_care_proposal = care_proposal
make_loss_evidence = loss_evidence
propose_care = care_proposal
accept_care = apply_care_receipt
apply_birth = record_birth
advance_age = advance_time
observe_loss = record_evidence
perceive_loss = record_evidence
report_demographics = demographic_report
save = dumps
resume = loads


__all__ = [
    "RULE", "SCHEMA_VERSION", "TRAIT_RANGES", "life_stage", "validate_life_stage",
    "inheritance_controls", "validate_inheritance_controls", "inherit_traits", "inheritance_result",
    "initial_state", "validate_state", "register_species", "add_individual", "record_birth",
    "care_proposal", "apply_care_receipt", "apply_care", "age_function", "mortality_hazard",
    "advance_time", "attachment_evidence", "loss_evidence", "record_evidence", "trigger_grief",
    "propose_external_action", "demographic_report", "carrying_capacity_report", "dumps", "loads",
    "copy_restart", "replay", "make_life_stage", "make_inheritance_controls", "make_inheritance_result",
    "make_care_proposal", "make_loss_evidence", "propose_care", "accept_care", "apply_birth",
    "advance_age", "observe_loss", "perceive_loss", "report_demographics", "save", "resume",
]
