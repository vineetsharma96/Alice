"""F6 directional relationship estimates from permitted witnessed events only."""
from copy import deepcopy
import math


RULE = "alice-relationships-f6-1"
MAX_EVIDENCE = 32
KINDS = frozenset({
    "heard", "shared_activity", "resource_given", "task_offered",
    "task_accepted", "task_completed", "task_declined", "task_expired",
    "task_failed",
})
POSITIVE = frozenset({"resource_given", "task_completed"})
NEGATIVE = frozenset({"task_declined", "task_expired", "task_failed"})


def _person(value, label):
    if type(value) is not str or not value or len(value) > 64:
        raise ValueError(f"Invalid relationship {label}")
    return value


def initial(owner, other):
    owner, other = _person(owner, "owner"), _person(other, "other")
    if owner == other:
        raise ValueError("A relationship needs two distinct inhabitants")
    return {
        "rule": RULE,
        "owner": owner,
        "other": other,
        "familiarity": 0.0,
        "trust": 0.0,
        "attachment": 0.0,
        "uncertainty": {"familiarity": 1.0, "trust": 1.0, "attachment": 1.0},
        "reliability": 0.0,
        "observations": 0,
        "positive": 0,
        "negative": 0,
        "shared_activity": 0,
        "evidence": [],
        "last_event": None,
        "origin": "directional own witnessed events; target private state is unavailable",
    }


def validate(state):
    expected = {
        "rule", "owner", "other", "familiarity", "trust", "attachment",
        "uncertainty", "reliability", "observations", "positive", "negative",
        "shared_activity", "evidence", "last_event", "origin",
    }
    if set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F6 relationship schema")
    _person(state["owner"], "owner")
    _person(state["other"], "other")
    if state["owner"] == state["other"]:
        raise ValueError("Self-relationships are not valid")
    for key in ("familiarity", "trust", "attachment", "reliability"):
        value = state[key]
        low, high = (-1.0, 1.0) if key == "trust" else (0.0, 1.0)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Invalid relationship {key}")
    if set(state["uncertainty"]) != {"familiarity", "trust", "attachment"}:
        raise ValueError("Invalid relationship uncertainty")
    if any(type(state["uncertainty"][k]) not in (int, float) or
           not math.isfinite(state["uncertainty"][k]) or
           not 0.0 <= state["uncertainty"][k] <= 1.0
           for k in state["uncertainty"]):
        raise ValueError("Invalid relationship uncertainty")
    for key in ("observations", "positive", "negative", "shared_activity"):
        if type(state[key]) is not int or state[key] < 0:
            raise ValueError("Invalid relationship counters")
    if state["positive"] + state["negative"] > state["observations"]:
        raise ValueError("Relationship outcome counters exceed observations")
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("Relationship evidence bound exceeded")
    ids = []
    for evidence in state["evidence"]:
        if set(evidence) != {"source_event_seq", "kind", "tick"}:
            raise ValueError("Invalid relationship evidence")
        if type(evidence["source_event_seq"]) is not str or not evidence["source_event_seq"]:
            raise ValueError("Invalid relationship evidence identity")
        if evidence["kind"] not in KINDS or type(evidence["tick"]) is not int or evidence["tick"] < 0:
            raise ValueError("Invalid relationship evidence")
        ids.append(evidence["source_event_seq"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate relationship evidence")
    if state["last_event"] is not None and state["last_event"] not in ids:
        raise ValueError("Relationship last event is not retained evidence")
    return state


def observe(state, event):
    """Apply one observer-owned, native-reported social event."""
    validate(state)
    if type(event) is not dict or set(event) != {"observer", "other", "kind", "source_event_seq", "tick"}:
        raise ValueError("F6 events must not contain private target state")
    if event["observer"] != state["owner"] or event["other"] != state["other"]:
        raise ValueError("Foreign relationship event")
    if event["kind"] not in KINDS or type(event["source_event_seq"]) is not str or not event["source_event_seq"]:
        raise ValueError("Invalid relationship event")
    if type(event["tick"]) is not int or event["tick"] < 0:
        raise ValueError("Invalid relationship event tick")
    if any(e["source_event_seq"] == event["source_event_seq"] for e in state["evidence"]):
        return None

    state["observations"] += 1
    kind = event["kind"]
    if kind in POSITIVE:
        state["positive"] += 1
    if kind in NEGATIVE:
        state["negative"] += 1
    if kind == "shared_activity":
        state["shared_activity"] += 1
    state["familiarity"] = 1.0 - math.exp(-state["observations"] / 4.0)

    outcomes = state["positive"] + state["negative"]
    if outcomes:
        state["trust"] = (state["positive"] - state["negative"]) / (outcomes + 2.0)
        state["reliability"] = state["positive"] / outcomes
    else:
        state["trust"] = 0.0
        state["reliability"] = 0.0
    trust_confidence = 1.0 - math.exp(-outcomes / 3.0)
    attachment_basis = max(0, state["shared_activity"] + state["positive"] - state["negative"] - 1)
    state["attachment"] = min(1.0, attachment_basis / 8.0)
    state["uncertainty"] = {
        "familiarity": math.exp(-state["observations"] / 4.0),
        "trust": 1.0 - trust_confidence,
        "attachment": 1.0 if attachment_basis == 0 else math.exp(-attachment_basis / 4.0),
    }
    state["evidence"] = (state["evidence"] + [{
        "source_event_seq": event["source_event_seq"], "kind": kind, "tick": event["tick"]
    }])[-MAX_EVIDENCE:]
    state["last_event"] = event["source_event_seq"]
    validate(state)
    return deepcopy(state["evidence"][-1])


def choose_helper(relationships, candidates):
    """Choose among visible IDs using only the observer's directional estimates."""
    if not isinstance(relationships, dict):
        raise ValueError("Relationships must be a mapping")
    candidates = sorted({_person(candidate, "candidate") for candidate in candidates})
    if not candidates:
        return None
    scored = []
    for candidate in candidates:
        state = relationships.get(candidate)
        if state is None:
            score, confidence = 0.0, 0.0
        else:
            validate(state)
            confidence = 1.0 - state["uncertainty"]["trust"]
            score = (0.65 * state["trust"] * confidence +
                     0.20 * state["reliability"] +
                     0.10 * state["familiarity"] +
                     0.05 * state["attachment"])
        scored.append((score, candidate, confidence))
    score, candidate, confidence = max(scored, key=lambda row: (row[0], row[1]))
    return {
        "other": candidate,
        "score": score,
        "confidence": confidence,
        "origin": "directional witnessed relationship estimate; native feasibility still required",
    }
