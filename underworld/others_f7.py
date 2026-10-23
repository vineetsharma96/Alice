"""Bounded, directional inference about another inhabitant.

F7 deliberately operates on a narrow public-observation contract.  It does not
read or accept target mood, goals, memories, lexicon, inventory, or operator
labels as evidence.  The estimator is a pure additive slice and is not wired
into the native world or scheduler.
"""

from copy import deepcopy
import math


RULE = "alice-others-f7-1"
MAX_EVIDENCE = 32
MAX_CUES_PER_UPDATE = 16
MAX_ID_LENGTH = 128

DIMENSIONS = ("needs", "goals", "affect")
NEEDS = frozenset({"water", "food", "rest", "safety", "warmth", "cooling", "social_contact"})
GOALS = frozenset({"seek_water", "seek_food", "seek_rest", "seek_shelter", "avoid_hazard", "seek_help", "reconnect"})
AFFECT = frozenset({"distress", "fatigue", "fear", "relief", "calm", "curiosity"})

_LABELS = {"needs": NEEDS, "goals": GOALS, "affect": AFFECT}

# Every rule is authored and finite.  The signs are evidence for (+1) or
# against (-1) the named possibility, rather than claims about private state.
_VISIBLE_RULES = {
    "thirst_signal": (("needs", "water", 0.90), ("goals", "seek_water", 0.82), ("affect", "distress", 0.38)),
    "hunger_signal": (("needs", "food", 0.90), ("goals", "seek_food", 0.82), ("affect", "distress", 0.34)),
    "fatigue_signal": (("needs", "rest", 0.90), ("goals", "seek_rest", 0.82), ("affect", "fatigue", 0.80)),
    "injury_signal": (("needs", "safety", 0.82), ("goals", "seek_help", 0.64), ("affect", "distress", 0.70)),
    "cold_signal": (("needs", "warmth", 0.90), ("goals", "seek_shelter", 0.78), ("affect", "distress", 0.46)),
    "heat_signal": (("needs", "cooling", 0.90), ("goals", "seek_shelter", 0.62), ("affect", "distress", 0.40)),
    "seeking_shelter": (("needs", "safety", 0.68), ("goals", "seek_shelter", 0.90), ("affect", "fear", 0.42)),
    "watching_resource": (("goals", "seek_water", 0.22), ("goals", "seek_food", 0.22), ("affect", "curiosity", 0.24)),
    "calm_posture": (("affect", "calm", 0.52),),
    "withdrawal": (("needs", "social_contact", 0.28), ("goals", "reconnect", 0.22), ("affect", "fear", 0.24)),
    "drinking_observed": (("needs", "water", -0.82), ("goals", "seek_water", -0.64), ("affect", "relief", 0.46)),
    "eating_observed": (("needs", "food", -0.82), ("goals", "seek_food", -0.64), ("affect", "relief", 0.40)),
    "resting_observed": (("needs", "rest", -0.82), ("goals", "seek_rest", -0.64), ("affect", "fatigue", -0.64), ("affect", "calm", 0.30)),
    "safe_in_shelter": (("needs", "safety", -0.70), ("goals", "seek_shelter", -0.62), ("affect", "fear", -0.52), ("affect", "calm", 0.42)),
    "ambiguous_stillness": (("needs", "rest", 0.30), ("needs", "safety", 0.25), ("goals", "seek_rest", 0.24), ("goals", "avoid_hazard", 0.22), ("affect", "calm", 0.20), ("affect", "fear", 0.20)),
}

_SOCIAL_RULES = {
    "asked_for_water": (("needs", "water", 0.88), ("goals", "seek_water", 0.84)),
    "asked_for_food": (("needs", "food", 0.88), ("goals", "seek_food", 0.84)),
    "asked_for_rest": (("needs", "rest", 0.82), ("goals", "seek_rest", 0.78)),
    "asked_for_shelter": (("needs", "safety", 0.78), ("goals", "seek_shelter", 0.84)),
    "asked_for_help": (("needs", "safety", 0.70), ("goals", "seek_help", 0.84)),
    "requested_company": (("needs", "social_contact", 0.76), ("goals", "reconnect", 0.72)),
    "accepted_help": (("needs", "safety", -0.34), ("affect", "relief", 0.36)),
    "declined_help": (("needs", "safety", 0.20), ("affect", "fear", 0.16)),
    "shared_resource": (("needs", "social_contact", -0.16), ("affect", "calm", 0.24)),
    "withdrew": (("needs", "social_contact", 0.22), ("goals", "reconnect", 0.18), ("affect", "fear", 0.20)),
    "warning_given": (("needs", "safety", 0.20), ("goals", "avoid_hazard", 0.46), ("affect", "fear", 0.22)),
}

_ALL_CUES = frozenset(_VISIBLE_RULES)
_ALL_REPORTS = frozenset(_SOCIAL_RULES)


def _person(value, label):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH:
        raise ValueError(f"Invalid F7 {label}")
    return value


def _event_id(value):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH:
        raise ValueError("Invalid F7 source event ID")
    return value


def _strength(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("Invalid F7 evidence strength")
    return float(value)


def initial(observer, target):
    """Create one observer-owned, directional estimate for one target."""
    observer, target = _person(observer, "observer"), _person(target, "target")
    if observer == target:
        raise ValueError("F7 requires two distinct inhabitants")
    return {
        "rule": RULE,
        "observer": observer,
        "target": target,
        "revision": 0,
        "evidence": [],
        "estimates": {dimension: {} for dimension in DIMENSIONS},
        "ambiguities": [],
        "last_update": [],
        "origin": "directional public observation only; target private state is unavailable",
    }


def validate(state):
    expected = {"rule", "observer", "target", "revision", "evidence", "estimates", "ambiguities", "last_update", "origin"}
    if type(state) is not dict or set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F7 inference schema")
    _person(state["observer"], "observer")
    _person(state["target"], "target")
    if state["observer"] == state["target"]:
        raise ValueError("F7 requires two distinct inhabitants")
    if type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("Invalid F7 revision")
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("F7 evidence bound exceeded")
    ids = []
    for item in state["evidence"]:
        if type(item) is not dict or set(item) != {"source_event_id", "channel", "signal", "strength"}:
            raise ValueError("F7 evidence must contain public fields only")
        _event_id(item["source_event_id"])
        if item["channel"] not in {"visible", "social"} or type(item["signal"]) is not str:
            raise ValueError("Invalid F7 evidence")
        _strength(item["strength"])
        ids.append(item["source_event_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate F7 source event ID")
    if set(state["estimates"]) != set(DIMENSIONS):
        raise ValueError("Invalid F7 estimate dimensions")
    for dimension in DIMENSIONS:
        if type(state["estimates"][dimension]) is not dict:
            raise ValueError("Invalid F7 estimate collection")
        for label, estimate in state["estimates"][dimension].items():
            if label not in _LABELS[dimension] or type(estimate) is not dict:
                raise ValueError("Invalid F7 estimate label")
            if set(estimate) != {"belief", "confidence", "uncertainty", "status", "provenance"}:
                raise ValueError("Invalid F7 estimate")
            if type(estimate["belief"]) not in (int, float) or not math.isfinite(estimate["belief"]) or not -1.0 <= estimate["belief"] <= 1.0:
                raise ValueError("Invalid F7 estimate belief")
            for key in ("confidence", "uncertainty"):
                if type(estimate[key]) not in (int, float) or not math.isfinite(estimate[key]) or not 0.0 <= estimate[key] <= 1.0:
                    raise ValueError("Invalid F7 estimate certainty")
            if estimate["status"] not in {"possible", "less_likely"} or type(estimate["provenance"]) is not list:
                raise ValueError("Invalid F7 estimate provenance")
            if any(item not in ids for item in estimate["provenance"]):
                raise ValueError("F7 estimate provenance is not retained evidence")
    if type(state["ambiguities"]) is not list or type(state["last_update"]) is not list:
        raise ValueError("Invalid F7 update metadata")
    if any(item not in ids for item in state["ambiguities"] + state["last_update"]):
        raise ValueError("F7 update metadata is not retained evidence")
    return state


def _validate_observation(state, observation):
    if type(observation) is not dict or set(observation) != {"observer", "target", "visible_cues", "social_reports"}:
        raise ValueError("F7 observation must contain only public observation fields")
    if observation["observer"] != state["observer"] or observation["target"] != state["target"]:
        raise ValueError("Foreign F7 observation")
    for key in ("visible_cues", "social_reports"):
        if type(observation[key]) is not list or len(observation[key]) > MAX_CUES_PER_UPDATE:
            raise ValueError("F7 observation batch is too large")

    events = []
    for item in observation["visible_cues"]:
        if type(item) is not dict or set(item) != {"source_event_id", "cue", "strength"}:
            raise ValueError("F7 visible cues must contain only public fields")
        source_event_id = _event_id(item["source_event_id"])
        if item["cue"] not in _ALL_CUES:
            raise ValueError("Unknown F7 visible cue")
        events.append({"source_event_id": source_event_id, "channel": "visible", "signal": item["cue"], "strength": _strength(item["strength"])})
    for item in observation["social_reports"]:
        if type(item) is not dict or set(item) != {"source_event_id", "kind", "strength"}:
            raise ValueError("F7 social reports must contain only witnessed public fields")
        source_event_id = _event_id(item["source_event_id"])
        if item["kind"] not in _ALL_REPORTS:
            raise ValueError("Unknown F7 social report")
        events.append({"source_event_id": source_event_id, "channel": "social", "signal": item["kind"], "strength": _strength(item["strength"])})
    ids = [item["source_event_id"] for item in events]
    if len(ids) != len(set(ids)) or any(item["source_event_id"] in {e["source_event_id"] for e in state["evidence"]} for item in events):
        raise ValueError("Duplicate F7 source event ID")
    return sorted(events, key=lambda item: (item["source_event_id"], item["channel"], item["signal"]))


def _contributions(item):
    rules = _VISIBLE_RULES if item["channel"] == "visible" else _SOCIAL_RULES
    return [(dimension, label, weight * item["strength"])
            for dimension, label, weight in rules[item["signal"]]]


def _compute(evidence):
    totals = {(dimension, label): 0.0 for dimension in DIMENSIONS for label in _LABELS[dimension]}
    provenance = {(dimension, label): [] for dimension in DIMENSIONS for label in _LABELS[dimension]}
    for item in evidence:
        for dimension, label, contribution in _contributions(item):
            totals[(dimension, label)] = max(-1.0, min(1.0, totals[(dimension, label)] + contribution))
            provenance[(dimension, label)].append(item["source_event_id"])

    estimates = {dimension: {} for dimension in DIMENSIONS}
    for dimension in DIMENSIONS:
        for label in sorted(_LABELS[dimension]):
            belief = totals[(dimension, label)]
            sources = sorted(provenance[(dimension, label)])
            if not sources or abs(belief) < 0.08:
                continue
            confidence = min(0.99, abs(belief) * (0.70 + 0.10 * min(len(sources), 3)))
            estimates[dimension][label] = {
                "belief": round(belief, 6),
                "confidence": round(confidence, 6),
                "uncertainty": round(1.0 - confidence, 6),
                "status": "possible" if belief >= 0 else "less_likely",
                "provenance": sources,
            }
    ambiguities = sorted(item["source_event_id"] for item in evidence if item["signal"] == "ambiguous_stillness")
    return estimates, ambiguities


def infer(state, observation, *, operator_label=None):
    """Apply public evidence and return a copy of the directional inference.

    ``operator_label`` is intentionally ignored.  It is transport metadata,
    never evidence, so changing it cannot change the result.
    """
    validate(state)
    events = _validate_observation(state, observation)
    before = deepcopy(state["estimates"])
    state["evidence"] = (state["evidence"] + events)[-MAX_EVIDENCE:]
    state["estimates"], state["ambiguities"] = _compute(state["evidence"])
    state["revision"] += 1 if events else 0
    state["last_update"] = [item["source_event_id"] for item in events]
    validate(state)
    changed = before != state["estimates"]
    result = deepcopy(state)
    result["changed"] = changed
    result["correction"] = {"applied": changed and bool(before), "source_event_ids": list(result["last_update"])}
    return result


__all__ = ["RULE", "MAX_EVIDENCE", "initial", "validate", "infer"]
