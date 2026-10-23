"""Pure, bounded F10 social and self-evaluative emotion states.

F10 is an additive offline overlay.  It records only the owner's strict public
 observations and relationship/evidence records.  An emotion is represented
 only after its authored prerequisite set is satisfied by linked evidence;
 otherwise it remains deferred and is not inserted into ``state["states"]``.
 Returned influence values are bounded proposals for an external native
 authority.  This module never reads private target state or executes actions.
"""

from copy import deepcopy
import math
import re


RULE = "alice-social-emotions-f10-1"
MAX_EVIDENCE = 32
MAX_SEEN_EVIDENCE = 128
MAX_ID_LENGTH = 128
MAX_CANDIDATES = 16

EMOTIONS = (
    "gratitude",
    "pride",
    "guilt",
    "embarrassment",
    "envy",
    "grief",
)
_EMOTION_SET = frozenset(EMOTIONS)
_PROVENANCE = frozenset({"seeded", "taught", "learned"})
_KINDS = frozenset({"own_observation", "relationship"})
_ACTIONS = frozenset({"repair", "gratitude", "avoid_concealment", "seek_connection"})
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_FORBIDDEN_PARTS = (
    "private", "hidden", "secret", "operator", "llm", "model", "prompt",
    "target_state", "foreign_state", "other_state",
)

# A finite public vocabulary.  Aliases are still authored vocabulary, not
# arbitrary emotion claims or free-form model output.
_PREDICATES = {
    "received_help",
    "recognized_benefit",
    "completed_achievement",
    "represented_standard",
    "perceived_responsibility",
    "violated_expectation",
    "feasible_repair",
    "public_exposure",
    "represented_norm",
    "observed_other_benefit",
    "self_relevant_comparison",
    "established_attachment",
    "loss_observed",
}
_PREDICATE_ALIASES = {
    "help_received": "received_help",
    "benefit_recognized": "recognized_benefit",
    "own_attributable_completed_achievement": "completed_achievement",
    "attributable_achievement": "completed_achievement",
    "standard_represented": "represented_standard",
    "responsibility_perceived": "perceived_responsibility",
    "expectation_violated": "violated_expectation",
    "repair_feasible": "feasible_repair",
    "exposure_public": "public_exposure",
    "norm_represented": "represented_norm",
    "comparison_self_relevant": "self_relevant_comparison",
    "attachment_established": "established_attachment",
    "loss": "loss_observed",
}


def _text(value, label):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid F10 {label}")
    return value


def _predicate(value):
    if type(value) is not str:
        raise ValueError("Invalid F10 predicate")
    value = _PREDICATE_ALIASES.get(value, value)
    if value not in _PREDICATES:
        raise ValueError("Unsupported F10 public predicate")
    return value


def _reject_forbidden(value, label="value"):
    """Reject private-state, operator-label, and model transport escapes."""
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid F10 {label} field")
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_PARTS):
                raise ValueError("F10 private, foreign, operator, and model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item, label)
    elif isinstance(value, tuple):
        raise ValueError(f"F10 {label} must be JSON-copyable")


def _value(value):
    # Values are public native facts: a boolean assertion or a bounded scalar
    # reference.  Nested state, labels, and arbitrary model payloads are not.
    if type(value) is bool:
        return value
    if type(value) is str and value and len(value) <= MAX_ID_LENGTH and _ID_RE.fullmatch(value):
        return value
    if type(value) in (int, float) and math.isfinite(float(value)) and 0.0 <= float(value) <= 1.0:
        return float(value)
    raise ValueError("Invalid F10 public evidence value")


def _affirmative(value):
    return not (value is False or value == 0 or value == "")


def _canonical_event(event):
    if type(event) is not dict:
        raise ValueError("F10 event must be a mapping")
    _reject_forbidden(event, "event")
    required = {"evidence_id", "kind", "owner", "run_id", "provenance", "predicate", "subject", "value", "other"}
    if set(event) != required:
        raise ValueError("F10 events must contain only strict public/native fields")
    evidence_id = _text(event["evidence_id"], "evidence_id")
    kind = event["kind"]
    if kind not in _KINDS:
        raise ValueError("Invalid F10 event kind")
    owner = _text(event["owner"], "event owner")
    run_id = _text(event["run_id"], "event run_id")
    if event["provenance"] not in _PROVENANCE:
        raise ValueError("F10 evidence provenance must be seeded, taught, or learned")
    predicate = _predicate(event["predicate"])
    subject = _text(event["subject"], "subject")
    value = _value(event["value"])
    other = event["other"]
    if kind == "own_observation":
        if other is not None:
            raise ValueError("F10 own observations cannot assert a relationship target")
    else:
        other = _text(other, "relationship other")
        if other == owner:
            raise ValueError("F10 relationships require a distinct other identity")
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "owner": owner,
        "run_id": run_id,
        "provenance": event["provenance"],
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "other": other,
    }


def _find(events, predicate, *, kind=None, subject=None, other=None):
    result = []
    for event in events:
        if event["predicate"] != predicate:
            continue
        if kind is not None and event["kind"] != kind:
            continue
        if subject is not None and event["subject"] != subject:
            continue
        if other is not None and event["other"] != other:
            continue
        if not _affirmative(event["value"]):
            continue
        result.append(event)
    return result


def _same_context(left, right, *, match_subject=True, match_other=False):
    if match_subject and left["subject"] != right["subject"]:
        return False
    if match_other and left["other"] != right["other"]:
        return False
    if left["other"] is not None and right["other"] is not None and left["other"] != right["other"]:
        return False
    return True


def _group(events, emotion):
    """Return linked prerequisite evidence for one emotion, or ``None``."""
    if emotion == "gratitude":
        for help_event in _find(events, "received_help"):
            for benefit_event in _find(events, "recognized_benefit"):
                if _same_context(help_event, benefit_event, match_subject=True):
                    return [help_event, benefit_event]
    elif emotion == "pride":
        for achievement in _find(events, "completed_achievement", kind="own_observation"):
            for standard in _find(events, "represented_standard", kind="own_observation"):
                if _same_context(achievement, standard, match_subject=True):
                    return [achievement, standard]
    elif emotion == "guilt":
        for responsibility in _find(events, "perceived_responsibility", kind="own_observation"):
            for violation in _find(events, "violated_expectation", kind="own_observation"):
                if not _same_context(responsibility, violation, match_subject=True):
                    continue
                for repair in _find(events, "feasible_repair", kind="own_observation"):
                    if _same_context(responsibility, repair, match_subject=True):
                        return [responsibility, violation, repair]
    elif emotion == "embarrassment":
        for exposure in _find(events, "public_exposure", kind="own_observation"):
            for norm in _find(events, "represented_norm", kind="own_observation"):
                if _same_context(exposure, norm, match_subject=True):
                    return [exposure, norm]
    elif emotion == "envy":
        for benefit in _find(events, "observed_other_benefit", kind="relationship"):
            for comparison in _find(events, "self_relevant_comparison"):
                if _same_context(benefit, comparison, match_subject=True, match_other=True):
                    return [benefit, comparison]
    elif emotion == "grief":
        for attachment in _find(events, "established_attachment", kind="relationship"):
            for loss in _find(events, "loss_observed", kind="relationship", other=attachment["other"]):
                # Attachment and loss are linked by the public relationship
                # identity.  The subject may differ (bond episode vs. loss event).
                return [attachment, loss]
    return None


def _derive(evidence):
    states = {}
    for emotion in EMOTIONS:
        group = _group(evidence, emotion)
        if not group:
            continue
        ids = sorted({item["evidence_id"] for item in group})
        tags = sorted({item["provenance"] for item in group})
        confidence = min(0.99, 0.50 + 0.10 * min(len(ids), 4))
        states[emotion] = {
            "score": 1.0,
            "confidence": round(confidence, 6),
            "evidence": ids,
            "provenance": tags,
        }
    return states


def _update_result(state, *, changed, evidence_id=None, removed=False):
    active = sorted(state["states"])
    deferred = {emotion: [] for emotion in EMOTIONS if emotion not in state["states"]}
    for emotion in deferred:
        # This is metadata about missing authored gates, not an emotion claim.
        required = {
            "gratitude": ("received_help", "recognized_benefit"),
            "pride": ("completed_achievement", "represented_standard"),
            "guilt": ("perceived_responsibility", "violated_expectation", "feasible_repair"),
            "embarrassment": ("public_exposure", "represented_norm"),
            "envy": ("observed_other_benefit", "self_relevant_comparison"),
            "grief": ("established_attachment", "loss_observed"),
        }[emotion]
        present = {item["predicate"] for item in state["evidence"] if _affirmative(item["value"])}
        deferred[emotion] = [predicate for predicate in required if predicate not in present]
    return {
        "changed": bool(changed),
        "evidence_id": evidence_id,
        "removed": bool(removed),
        "available": active,
        "deferred": deferred,
        "state": deepcopy(state),
    }


def initial(owner, run_id):
    """Create an empty F10 state for one owner/run pair."""
    owner, run_id = _text(owner, "owner"), _text(run_id, "run_id")
    return {
        "rule": RULE,
        "owner": owner,
        "run_id": run_id,
        "revision": 0,
        "evidence": [],
        "seen_evidence": [],
        "states": {},
        "last_update": [],
        "origin": "bounded prerequisite-gated states from own public evidence",
    }


def validate(state):
    expected = {
        "rule", "owner", "run_id", "revision", "evidence", "seen_evidence",
        "states", "last_update", "origin",
    }
    if type(state) is not dict or set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F10 social emotion schema")
    _text(state["owner"], "owner")
    _text(state["run_id"], "run_id")
    if type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("Invalid F10 revision")
    if type(state["origin"]) is not str or not state["origin"]:
        raise ValueError("Invalid F10 origin")
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("F10 evidence bound exceeded")
    if type(state["seen_evidence"]) is not list or len(state["seen_evidence"]) > MAX_SEEN_EVIDENCE:
        raise ValueError("F10 duplicate ledger bound exceeded")
    ids = []
    for event in state["evidence"]:
        canonical = _canonical_event(event)
        if canonical != event or event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
            raise ValueError("F10 evidence is foreign or non-canonical")
        ids.append(event["evidence_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate F10 evidence")
    seen_ids = []
    for event in state["seen_evidence"]:
        canonical = _canonical_event(event)
        if canonical != event or event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
            raise ValueError("F10 seen evidence is foreign or non-canonical")
        seen_ids.append(event["evidence_id"])
    if len(seen_ids) != len(set(seen_ids)):
        raise ValueError("Duplicate F10 evidence ledger entry")
    if any(evidence_id not in seen_ids for evidence_id in ids):
        raise ValueError("F10 retained evidence missing from duplicate ledger")
    if type(state["last_update"]) is not list or any(item not in seen_ids for item in state["last_update"]):
        raise ValueError("Invalid F10 last update")
    if type(state["states"]) is not dict or set(state["states"]) - _EMOTION_SET:
        raise ValueError("Invalid F10 state emotion set")
    for emotion, item in state["states"].items():
        if type(item) is not dict or set(item) != {"score", "confidence", "evidence", "provenance"}:
            raise ValueError("Invalid F10 represented emotion state")
        if type(item["score"]) not in (int, float) or not math.isfinite(item["score"]) or not 0.0 <= item["score"] <= 1.0:
            raise ValueError("Invalid F10 emotion score")
        if type(item["confidence"]) not in (int, float) or not math.isfinite(item["confidence"]) or not 0.0 <= item["confidence"] <= 1.0:
            raise ValueError("Invalid F10 emotion confidence")
        if type(item["evidence"]) is not list or not item["evidence"] or len(item["evidence"]) > MAX_EVIDENCE:
            raise ValueError("Invalid F10 emotion evidence links")
        if any(evidence_id not in ids for evidence_id in item["evidence"]):
            raise ValueError("F10 emotion evidence is not retained")
        if len(item["evidence"]) != len(set(item["evidence"])):
            raise ValueError("Duplicate F10 emotion evidence link")
        if type(item["provenance"]) is not list or not item["provenance"] or any(tag not in _PROVENANCE for tag in item["provenance"]):
            raise ValueError("Invalid F10 emotion provenance")
    expected_states = _derive(state["evidence"])
    if state["states"] != expected_states:
        raise ValueError("F10 represented states do not match prerequisite evidence")
    return state


def observe_event(state, event):
    """Record one owner-scoped public event and recompute gated states."""
    validate(state)
    event = _canonical_event(event)
    if event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
        raise ValueError("Foreign F10 event")
    existing = next((item for item in state["seen_evidence"] if item["evidence_id"] == event["evidence_id"]), None)
    if existing is not None:
        if existing != event:
            raise ValueError("Conflicting duplicate F10 evidence")
        return _update_result(state, changed=False, evidence_id=event["evidence_id"])
    before = deepcopy(state["states"])
    state["evidence"] = (state["evidence"] + [event])[-MAX_EVIDENCE:]
    state["seen_evidence"] = (state["seen_evidence"] + [deepcopy(event)])[-MAX_SEEN_EVIDENCE:]
    state["states"] = _derive(state["evidence"])
    state["revision"] += 1
    state["last_update"] = [event["evidence_id"]]
    validate(state)
    return _update_result(state, changed=before != state["states"], evidence_id=event["evidence_id"])


def available(state, emotion):
    """Return whether one authored emotion has all linked prerequisites."""
    validate(state)
    if type(emotion) is not str or emotion not in _EMOTION_SET:
        raise ValueError("Unsupported F10 emotion")
    return emotion in state["states"]


def _candidate(candidate):
    if type(candidate) is not dict:
        raise ValueError("F10 candidates must be mappings")
    _reject_forbidden(candidate, "candidate")
    if set(candidate) - {"action", "target"} or "action" not in candidate:
        raise ValueError("F10 candidates must contain only bounded action fields")
    if candidate["action"] not in _ACTIONS:
        raise ValueError("Unsupported F10 proposal action")
    if "target" in candidate:
        target = _text(candidate["target"], "candidate target")
        if target == "":
            raise ValueError("Invalid F10 candidate target")
    return deepcopy(candidate)


def _linked_others(state, emotion):
    item = state["states"].get(emotion)
    if item is None:
        return set()
    ids = set(item["evidence"])
    return {event["other"] for event in state["evidence"] if event["evidence_id"] in ids and event["other"] is not None}


def influence(state, candidates):
    """Return one external action proposal influenced by active gated states."""
    validate(state)
    if type(candidates) is not list or not candidates or len(candidates) > MAX_CANDIDATES:
        raise ValueError("F10 candidates must be a non-empty bounded list")
    parsed = [_candidate(candidate) for candidate in candidates]
    action_emotions = {
        "repair": ("guilt", 4),
        "gratitude": ("gratitude", 3),
        "avoid_concealment": ("embarrassment", 2),
        "seek_connection": ("grief", 1),
    }
    eligible = []
    for index, candidate in enumerate(parsed):
        emotion, priority = action_emotions[candidate["action"]]
        if emotion not in state["states"]:
            continue
        if "target" in candidate and candidate["target"] in _linked_others(state, emotion):
            target_ok = True
        elif "target" not in candidate or not _linked_others(state, emotion):
            target_ok = True
        else:
            target_ok = False
        if target_ok:
            eligible.append((priority, -index, candidate, emotion))
    if not eligible:
        return None
    _, _, candidate, emotion = max(eligible, key=lambda row: (row[0], row[1]))
    proposal = deepcopy(candidate)
    proposal.update({
        "emotion": emotion,
        "evidence": list(state["states"][emotion]["evidence"]),
        "execution": "external",
    })
    return proposal


def remove_evidence(state, evidence_id):
    """Remove one retained evidence record and recompute all gated states."""
    validate(state)
    evidence_id = _text(evidence_id, "evidence_id")
    if not any(item["evidence_id"] == evidence_id for item in state["evidence"]):
        raise ValueError("F10 evidence is not retained")
    before = deepcopy(state["states"])
    state["evidence"] = [item for item in state["evidence"] if item["evidence_id"] != evidence_id]
    state["seen_evidence"] = [item for item in state["seen_evidence"] if item["evidence_id"] != evidence_id]
    state["states"] = _derive(state["evidence"])
    state["revision"] += 1
    state["last_update"] = []
    validate(state)
    return _update_result(state, changed=before != state["states"], evidence_id=evidence_id, removed=True)


def correct_evidence(state, evidence_id, replacement):
    """Replace one retained event with a corrected same-ID public event."""
    validate(state)
    evidence_id = _text(evidence_id, "evidence_id")
    replacement = _canonical_event(replacement)
    if replacement["evidence_id"] != evidence_id:
        raise ValueError("F10 corrections must preserve evidence identity")
    if replacement["owner"] != state["owner"] or replacement["run_id"] != state["run_id"]:
        raise ValueError("Foreign F10 correction")
    retained_index = next((index for index, item in enumerate(state["evidence"])
                           if item["evidence_id"] == evidence_id), None)
    if retained_index is None:
        raise ValueError("F10 evidence is not retained")
    existing = state["evidence"][retained_index]
    if existing == replacement:
        return _update_result(state, changed=False, evidence_id=evidence_id)
    before = deepcopy(state["states"])
    state["evidence"][retained_index] = replacement
    for index, item in enumerate(state["seen_evidence"]):
        if item["evidence_id"] == evidence_id:
            state["seen_evidence"][index] = deepcopy(replacement)
            break
    state["states"] = _derive(state["evidence"])
    state["revision"] += 1
    state["last_update"] = [evidence_id]
    validate(state)
    return _update_result(state, changed=before != state["states"], evidence_id=evidence_id)


__all__ = [
    "RULE", "MAX_EVIDENCE", "MAX_SEEN_EVIDENCE", "EMOTIONS", "initial",
    "validate", "observe_event", "available", "influence", "remove_evidence",
    "correct_evidence",
]
