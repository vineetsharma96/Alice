"""Pure, bounded F11 identity and values overlay.

F11 keeps a small owner/run-scoped account of declared values, acquired
preferences, revisable summaries and long-term commitment proposals.  Only
strict public/native-shaped events can update acquired state.  This module is
copy-friendly JSON data: it never reads private state, executes an action, or
turns an emotional/self-report label into value credit.
"""

from copy import deepcopy
import math
import re


RULE = "alice-identity-values-f11-1"
MAX_EVIDENCE = 32
MAX_SEEN_EVIDENCE = 128
MAX_EVIDENCE_LINKS = 8
MAX_DECLARED_VALUES = 16
MAX_COMMITMENTS = 16
MAX_SUMMARY_CLAIMS = 8
MAX_SUMMARY_CONTEXTS = 8
MAX_REVISION_HISTORY = 16
MAX_CONTEXT_TAGS = 8
MAX_ID_LENGTH = 128
MAX_LABEL_LENGTH = 96
MAX_SUMMARY_TEXT = 256

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.: /-]{0,95}$")
_FORBIDDEN_PARTS = (
    "private", "hidden", "secret", "operator", "llm", "model", "prompt",
    "target_state", "foreign_state", "other_state", "self_report",
)
_KINDS = frozenset({"own_observation", "public_outcome", "native_outcome"})
_PROVENANCE = frozenset({
    "seeded", "taught", "learned", "native", "own_native_observation",
    "public_native_outcome",
})
_STATUSES = frozenset({
    "observed", "completed", "succeeded", "failed", "contrary", "reversed",
    "safe", "harmful", "helped", "kept", "neutral",
})
_POSITIVE = frozenset({"completed", "succeeded", "safe", "helped", "kept"})
_NEGATIVE = frozenset({"failed", "contrary", "reversed", "harmful"})
_EMOTIONAL_LABELS = frozenset({
    "anger", "embarrassment", "envy", "fear", "grief", "guilt", "joy",
    "love", "pride", "sadness", "shame", "gratitude", "happy", "sad",
    "afraid", "emotional",
})
_STATUS_ALIASES = {
    "success": "succeeded", "positive": "succeeded", "failure": "failed",
    "negative": "failed", "reversal": "reversed",
}


def _text(value, label):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid F11 {label}")
    return value


def _label(value, label, limit=MAX_LABEL_LENGTH):
    if type(value) is not str or not value or len(value) > limit or not _LABEL_RE.fullmatch(value):
        raise ValueError(f"Invalid F11 {label}")
    return value


def _short_text(value, label):
    if type(value) is not str or not value.strip() or len(value) > MAX_SUMMARY_TEXT:
        raise ValueError(f"Invalid F11 {label}")
    return value


def _finite(value, label, low=0.0, high=1.0):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"Invalid F11 {label}")
    value = float(value)
    if value < low or value > high:
        raise ValueError(f"Invalid F11 {label}")
    return value


def _reject_forbidden(value, label="value"):
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid F11 {label} field")
            lowered = key.lower()
            if any(part in lowered for part in _FORBIDDEN_PARTS):
                raise ValueError("F11 private, foreign, operator, and model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item, label)
    elif isinstance(value, tuple):
        raise ValueError(f"F11 {label} must be JSON-copyable")


def _tags(value, label, limit=MAX_CONTEXT_TAGS):
    if type(value) is not list or len(value) > limit:
        raise ValueError(f"Invalid F11 {label}")
    result = []
    for item in value:
        item = _label(item, label, 32)
        if item not in result:
            result.append(item)
    return result


def _canonical_event(event):
    if type(event) is not dict:
        raise ValueError("F11 event must be a mapping")
    _reject_forbidden(event, "event")
    aliases = {"subject": "value", "result": "outcome", "context_tags": "context", "source_id": "source"}
    allowed = {"evidence_id", "kind", "owner", "run_id", "provenance", "status", "value", "outcome", "context", "source"}
    if not set(event).issubset(allowed | set(aliases)):
        raise ValueError("F11 events must contain only strict public/native fields")
    item = dict(event)
    for alias, canonical in aliases.items():
        if alias in item:
            if canonical in item:
                raise ValueError("F11 event contains duplicate canonical and alias fields")
            item[canonical] = item.pop(alias)
    required = {"evidence_id", "kind", "owner", "run_id", "provenance", "status", "value", "outcome", "context", "source"}
    if set(item) != required:
        raise ValueError("F11 events require evidence, identity, provenance, status, value, context, and source")
    evidence_id = _text(item["evidence_id"], "evidence_id")
    kind = item["kind"]
    if kind == "public_native_outcome":
        kind = "native_outcome"
    if kind not in _KINDS:
        raise ValueError("Invalid F11 event kind")
    owner, run_id = _text(item["owner"], "event owner"), _text(item["run_id"], "event run_id")
    provenance = item["provenance"]
    if provenance not in _PROVENANCE:
        raise ValueError("Invalid F11 event provenance")
    status = _STATUS_ALIASES.get(item["status"], item["status"])
    if status not in _STATUSES:
        raise ValueError("Invalid F11 event status")
    value = _label(item["value"], "event value", 64)
    if value.lower() in _EMOTIONAL_LABELS:
        raise ValueError("F11 emotional labels are not value evidence")
    outcome = _label(item["outcome"], "event outcome", 96)
    outcome_lower = outcome.lower()
    if (any(term in outcome_lower for term in ("i feel", "i felt", "i value", "self report", "self-report", "emotion", "self-reward", "self reward", "self_reward", "value credit"))
            or any(label in outcome_lower.split() for label in _EMOTIONAL_LABELS)):
        raise ValueError("F11 self-report or circular self-reward outcome cannot create value credit")
    context = _tags(item["context"], "event context")
    source = _text(item["source"], "event source")
    if any(term in source.lower() for term in ("self_report", "self-report", "operator", "model", "private")):
        raise ValueError("F11 event source must be public/native provenance")
    return {
        "evidence_id": evidence_id, "kind": kind, "owner": owner, "run_id": run_id,
        "provenance": provenance, "status": status, "value": value,
        "outcome": outcome, "context": context, "source": source,
    }


def _empty_summary():
    return {
        "text": "", "claims": [], "contexts": [], "evidence": [],
        "confidence": 0.0, "uncertainty": 1.0,
    }


def _summary(value, evidence_ids=None):
    if type(value) is str:
        result = _empty_summary()
        result["text"] = _short_text(value, "summary text")
    elif type(value) is dict:
        _reject_forbidden(value, "summary")
        allowed = {"text", "claims", "contexts", "confidence", "uncertainty"}
        if not set(value).issubset(allowed):
            raise ValueError("F11 summary contains unsupported fields")
        result = _empty_summary()
        if "text" in value:
            result["text"] = _short_text(value["text"], "summary text")
        if "claims" in value:
            if type(value["claims"]) is not list or len(value["claims"]) > MAX_SUMMARY_CLAIMS:
                raise ValueError("F11 summary claims bound exceeded")
            result["claims"] = [_label(item, "summary claim", 64) for item in value["claims"]]
        if "contexts" in value:
            result["contexts"] = _tags(value["contexts"], "summary contexts", MAX_SUMMARY_CONTEXTS)
        if "confidence" in value:
            result["confidence"] = _finite(value["confidence"], "summary confidence")
        if "uncertainty" in value:
            result["uncertainty"] = _finite(value["uncertainty"], "summary uncertainty")
        if "confidence" in value and "uncertainty" in value:
            if round(result["confidence"] + result["uncertainty"], 6) != 1.0:
                raise ValueError("F11 summary confidence and uncertainty disagree")
        elif "confidence" in value:
            result["uncertainty"] = round(1.0 - result["confidence"], 6)
        elif "uncertainty" in value:
            result["confidence"] = round(1.0 - result["uncertainty"], 6)
    else:
        raise ValueError("F11 summary must be text or a bounded mapping")
    if evidence_ids is not None:
        result["evidence"] = list(dict.fromkeys(evidence_ids))[-MAX_EVIDENCE_LINKS:]
        if (type(value) is not dict) or ("confidence" not in value):
            result["confidence"] = round(min(0.99, 0.20 + 0.12 * len(result["evidence"])), 6)
            result["uncertainty"] = round(1.0 - result["confidence"], 6)
    return result


def _sign(status):
    if status in _POSITIVE:
        return 1
    if status in _NEGATIVE:
        return -1
    return 0


def _derive(state):
    grouped = {}
    for event in state["evidence"]:
        sign = _sign(event["status"])
        if not sign:
            continue
        entry = grouped.setdefault(event["value"], {"score": 0, "positive": 0, "negative": 0, "evidence": [], "contexts": []})
        entry["score"] = max(-MAX_EVIDENCE, min(MAX_EVIDENCE, entry["score"] + sign))
        entry["positive" if sign > 0 else "negative"] += 1
        entry["evidence"] = (entry["evidence"] + [event["evidence_id"]])[-MAX_EVIDENCE_LINKS:]
        entry["contexts"] = list(dict.fromkeys(entry["contexts"] + event["context"]))[-MAX_CONTEXT_TAGS:]
    preferences = {}
    commitments = {}
    for value, raw in grouped.items():
        magnitude = abs(raw["score"])
        confidence = round(min(0.99, 0.20 + 0.12 * min(len(raw["evidence"]), 5) + 0.08 * min(magnitude, 4)), 6)
        entry = {
            "score": raw["score"], "positive": raw["positive"], "negative": raw["negative"],
            "confidence": confidence, "uncertainty": round(1.0 - confidence, 6),
            "evidence": list(raw["evidence"]), "contexts": list(raw["contexts"]),
        }
        preferences[value] = entry
        if raw["score"] > 0:
            commitments[value] = {
                "commitment_id": value, "value": value, "status": "active",
                "basis": "acquired", "confidence": confidence,
                "uncertainty": round(1.0 - confidence, 6),
                "evidence": list(raw["evidence"]), "contexts": list(raw["contexts"]),
            }
    return preferences, commitments


def _find_seen(state, evidence_id):
    return next((item for item in state["seen_evidence"] if item["evidence_id"] == evidence_id), None)


def _record_history(state, kind, evidence_id=None):
    state["revision"] += 1
    state["revision_history"] = (state["revision_history"] + [{
        "revision": state["revision"], "kind": kind, "evidence_id": evidence_id,
    }])[-MAX_REVISION_HISTORY:]


def initial(owner, run_id, declared_values):
    """Create an empty owner/run state with authored declared values only."""
    owner, run_id = _text(owner, "owner"), _text(run_id, "run_id")
    if type(declared_values) not in (list, tuple) or len(declared_values) > MAX_DECLARED_VALUES:
        raise ValueError("F11 declared values must be a bounded list")
    declared = []
    for value in declared_values:
        value = _label(value, "declared value", 64)
        if value not in declared:
            declared.append(value)
    return {
        "rule": RULE, "owner": owner, "run_id": run_id, "revision": 0,
        "declared_values": declared, "acquired_preferences": {}, "commitments": {},
        "summary": _empty_summary(), "evidence": [], "seen_evidence": [],
        "revision_history": [], "last_update": [],
        "origin": "declared values remain separate from preferences acquired from retained public/native evidence",
    }


def validate(state):
    expected = {
        "rule", "owner", "run_id", "revision", "declared_values", "acquired_preferences",
        "commitments", "summary", "evidence", "seen_evidence", "revision_history",
        "last_update", "origin",
    }
    if type(state) is not dict or set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F11 identity/values schema")
    _text(state["owner"], "owner")
    _text(state["run_id"], "run_id")
    if type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("Invalid F11 revision")
    if type(state["origin"]) is not str or not state["origin"]:
        raise ValueError("Invalid F11 origin")
    if type(state["declared_values"]) is not list or len(state["declared_values"]) > MAX_DECLARED_VALUES:
        raise ValueError("F11 declared values bound exceeded")
    for value in state["declared_values"]:
        _label(value, "declared value", 64)
    if len(state["declared_values"]) != len(set(state["declared_values"])):
        raise ValueError("Duplicate F11 declared value")
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("F11 evidence bound exceeded")
    if type(state["seen_evidence"]) is not list or len(state["seen_evidence"]) > MAX_SEEN_EVIDENCE:
        raise ValueError("F11 duplicate ledger bound exceeded")
    ids = []
    for event in state["evidence"]:
        canonical = _canonical_event(event)
        if canonical != event or event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
            raise ValueError("F11 retained evidence is foreign or non-canonical")
        ids.append(event["evidence_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate F11 evidence")
    seen_ids = []
    for event in state["seen_evidence"]:
        canonical = _canonical_event(event)
        if canonical != event or event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
            raise ValueError("F11 seen evidence is foreign or non-canonical")
        seen_ids.append(event["evidence_id"])
    if len(seen_ids) != len(set(seen_ids)):
        raise ValueError("Duplicate F11 evidence ledger entry")
    if any(item not in seen_ids for item in ids):
        raise ValueError("F11 retained evidence missing from duplicate ledger")
    if type(state["last_update"]) is not list or any(item not in seen_ids for item in state["last_update"]):
        raise ValueError("Invalid F11 last update")
    _validate_summary(state["summary"], ids)
    if type(state["revision_history"]) is not list or len(state["revision_history"]) > MAX_REVISION_HISTORY:
        raise ValueError("F11 revision history bound exceeded")
    for item in state["revision_history"]:
        if type(item) is not dict or set(item) != {"revision", "kind", "evidence_id"}:
            raise ValueError("Invalid F11 revision history")
        if type(item["revision"]) is not int or item["revision"] < 1 or item["revision"] > state["revision"]:
            raise ValueError("Invalid F11 revision history number")
        if item["kind"] not in {"event", "summary", "correction", "removal"}:
            raise ValueError("Invalid F11 revision history kind")
        if item["evidence_id"] is not None:
            _text(item["evidence_id"], "history evidence_id")
    if type(state["acquired_preferences"]) is not dict or len(state["acquired_preferences"]) > MAX_COMMITMENTS:
        raise ValueError("F11 preference bound exceeded")
    for value, item in state["acquired_preferences"].items():
        _label(value, "preference value", 64)
        _validate_preference(item, ids)
    if type(state["commitments"]) is not dict or len(state["commitments"]) > MAX_COMMITMENTS:
        raise ValueError("F11 commitment bound exceeded")
    for value, item in state["commitments"].items():
        _label(value, "commitment value", 64)
        if type(item) is not dict or set(item) != {"commitment_id", "value", "status", "basis", "confidence", "uncertainty", "evidence", "contexts"}:
            raise ValueError("Invalid F11 commitment")
        if item["commitment_id"] != value or item["value"] != value or item["status"] != "active" or item["basis"] != "acquired":
            raise ValueError("Invalid F11 commitment identity or status")
        _finite(item["confidence"], "commitment confidence")
        _finite(item["uncertainty"], "commitment uncertainty")
        if round(item["confidence"] + item["uncertainty"], 6) != 1.0:
            raise ValueError("Inconsistent F11 commitment confidence")
        _links(item["evidence"], ids, "commitment evidence")
        _tags(item["contexts"], "commitment contexts")
    preferences, commitments = _derive(state)
    if state["acquired_preferences"] != preferences or state["commitments"] != commitments:
        raise ValueError("F11 acquired state is not derived from retained evidence")
    return state


def _links(value, ids, label):
    if type(value) is not list or len(value) > MAX_EVIDENCE_LINKS or len(value) != len(set(value)):
        raise ValueError(f"Invalid F11 {label}")
    for item in value:
        _text(item, label)
        if item not in ids:
            raise ValueError(f"F11 {label} is not retained")


def _validate_preference(item, ids):
    required = {"score", "positive", "negative", "confidence", "uncertainty", "evidence", "contexts"}
    if type(item) is not dict or set(item) != required:
        raise ValueError("Invalid F11 acquired preference")
    if type(item["score"]) is not int or not -MAX_EVIDENCE <= item["score"] <= MAX_EVIDENCE:
        raise ValueError("Invalid F11 preference score")
    for key in ("positive", "negative"):
        if type(item[key]) is not int or item[key] < 0:
            raise ValueError("Invalid F11 preference count")
    _finite(item["confidence"], "preference confidence")
    _finite(item["uncertainty"], "preference uncertainty")
    if round(item["confidence"] + item["uncertainty"], 6) != 1.0:
        raise ValueError("Inconsistent F11 preference confidence")
    _links(item["evidence"], ids, "preference evidence")
    _tags(item["contexts"], "preference contexts")


def _validate_summary(item, ids):
    if type(item) is not dict or set(item) != {"text", "claims", "contexts", "evidence", "confidence", "uncertainty"}:
        raise ValueError("Invalid F11 summary")
    if item["text"] and (type(item["text"]) is not str or len(item["text"]) > MAX_SUMMARY_TEXT):
        raise ValueError("Invalid F11 summary text")
    if type(item["claims"]) is not list or len(item["claims"]) > MAX_SUMMARY_CLAIMS:
        raise ValueError("F11 summary claims bound exceeded")
    for claim in item["claims"]:
        _label(claim, "summary claim", 64)
    _tags(item["contexts"], "summary contexts", MAX_SUMMARY_CONTEXTS)
    _links(item["evidence"], ids, "summary evidence")
    _finite(item["confidence"], "summary confidence")
    _finite(item["uncertainty"], "summary uncertainty")
    if round(item["confidence"] + item["uncertainty"], 6) != 1.0:
        raise ValueError("Inconsistent F11 summary confidence")


def observe_event(state, event):
    """Record one owner-scoped public/native event and derive preferences."""
    validate(state)
    event = _canonical_event(event)
    if event["owner"] != state["owner"] or event["run_id"] != state["run_id"]:
        raise ValueError("Foreign F11 event")
    existing = _find_seen(state, event["evidence_id"])
    if existing is not None:
        if existing != event:
            raise ValueError("Conflicting duplicate F11 evidence")
        return {"changed": False, "evidence_id": event["evidence_id"], "state": deepcopy(state)}
    if len(state["evidence"]) >= MAX_EVIDENCE:
        state["evidence"] = state["evidence"][1:]
    state["evidence"].append(event)
    if len(state["seen_evidence"]) >= MAX_SEEN_EVIDENCE:
        state["seen_evidence"] = state["seen_evidence"][1:]
    state["seen_evidence"].append(deepcopy(event))
    state["acquired_preferences"], state["commitments"] = _derive(state)
    state["last_update"] = [event["evidence_id"]]
    _record_history(state, "event", event["evidence_id"])
    _refresh_summary_links(state)
    validate(state)
    return {"changed": True, "evidence_id": event["evidence_id"], "state": deepcopy(state)}


def _refresh_summary_links(state):
    retained = {item["evidence_id"] for item in state["evidence"]}
    state["summary"]["evidence"] = [item for item in state["summary"]["evidence"] if item in retained]
    links = len(state["summary"]["evidence"])
    if links:
        state["summary"]["confidence"] = round(min(state["summary"]["confidence"], 0.20 + 0.12 * links), 6)
        state["summary"]["uncertainty"] = round(1.0 - state["summary"]["confidence"], 6)


def revise_summary(state, summary, evidence_id):
    """Replace the personal summary using one retained evidence link."""
    validate(state)
    evidence_id = _text(evidence_id, "evidence_id")
    if evidence_id not in {item["evidence_id"] for item in state["evidence"]}:
        raise ValueError("F11 summary evidence is not retained")
    current_links = [item for item in state["summary"]["evidence"] if item in {e["evidence_id"] for e in state["evidence"]}]
    next_summary = _summary(summary, current_links + [evidence_id])
    if next_summary == state["summary"]:
        return {"changed": False, "evidence_id": evidence_id, "summary": deepcopy(state["summary"])}
    state["summary"] = next_summary
    state["last_update"] = [evidence_id]
    _record_history(state, "summary", evidence_id)
    validate(state)
    return {"changed": True, "evidence_id": evidence_id, "summary": deepcopy(state["summary"])}


def _observation(observation):
    if type(observation) is not dict:
        raise ValueError("F11 observation must be a mapping")
    _reject_forbidden(observation, "observation")
    aliases = {"agent_id": "owner", "context_tags": "context"}
    if not set(observation).issubset({"owner", "run_id", "context", "context_tags", "agent_id", "feasible"}):
        raise ValueError("F11 observation contains unsupported fields")
    item = dict(observation)
    for alias, canonical in aliases.items():
        if alias in item:
            if canonical in item:
                raise ValueError("F11 observation contains duplicate identity/context fields")
            item[canonical] = item.pop(alias)
    if set(item) - {"owner", "run_id", "context", "feasible"} or "owner" not in item or "run_id" not in item:
        raise ValueError("F11 observation requires owner and run_id")
    item["owner"], item["run_id"] = _text(item["owner"], "observation owner"), _text(item["run_id"], "observation run_id")
    item["context"] = _tags(item.get("context", []), "observation context")
    if "feasible" in item and type(item["feasible"]) is not bool:
        raise ValueError("Invalid F11 observation feasibility")
    return item


def _candidate(candidate, owner, run_id):
    if type(candidate) is not dict:
        raise ValueError("F11 candidates must be mappings")
    _reject_forbidden(candidate, "candidate")
    allowed = {"action", "value", "commitment", "owner", "run_id", "feasible", "context", "context_tags", "metadata", "target"}
    if not set(candidate).issubset(allowed) or "action" not in candidate:
        raise ValueError("F11 candidates need a bounded action")
    item = deepcopy(candidate)
    metadata = item.pop("metadata", {})
    if type(metadata) is not dict:
        raise ValueError("F11 candidate metadata must be a mapping")
    _reject_forbidden(metadata, "candidate metadata")
    if set(metadata) - {"owner", "run_id", "context", "context_tags", "feasible"}:
        raise ValueError("F11 candidate metadata contains unsupported fields")
    candidate_owner = item.get("owner", metadata.get("owner", owner))
    candidate_run = item.get("run_id", metadata.get("run_id", run_id))
    if candidate_owner != owner or candidate_run != run_id:
        raise ValueError("Foreign F11 candidate metadata")
    item["owner"], item["run_id"] = owner, run_id
    item["context"] = _tags(item.get("context", item.get("context_tags", metadata.get("context", metadata.get("context_tags", [])))), "candidate context")
    item["feasible"] = item.get("feasible", metadata.get("feasible", True))
    if type(item["feasible"]) is not bool:
        raise ValueError("Invalid F11 candidate feasibility")
    value = item.get("value", item.get("commitment", item["action"]))
    item["value"] = _label(value, "candidate value", 64)
    _label(item["action"], "candidate action", 64)
    return item


def choose_commitment_action(state, observation, candidates):
    """Return one feasible, owner/run-matched external commitment proposal."""
    validate(state)
    observation = _observation(observation)
    if observation["owner"] != state["owner"] or observation["run_id"] != state["run_id"]:
        raise ValueError("Foreign F11 observation")
    if type(candidates) is not list or not candidates or len(candidates) > 16:
        raise ValueError("F11 candidates must be a non-empty bounded list")
    parsed = [_candidate(candidate, state["owner"], state["run_id"]) for candidate in candidates]
    available = []
    for index, candidate in enumerate(parsed):
        if not candidate["feasible"]:
            continue
        value = candidate["value"]
        acquired = state["acquired_preferences"].get(value)
        declared = value in state["declared_values"]
        if acquired is None and not declared:
            continue
        if acquired is not None and acquired["score"] <= 0 and not declared:
            continue
        score = 0.25 if declared else 0.0
        evidence = []
        confidence = 0.0
        uncertainty = 1.0
        basis = "declared_value"
        if acquired is not None and acquired["score"] > 0:
            basis = "acquired_commitment"
            score += float(acquired["score"])
            evidence = list(acquired["evidence"])
            confidence = acquired["confidence"]
            uncertainty = acquired["uncertainty"]
            overlap = set(candidate["context"]) & set(acquired["contexts"])
            if overlap:
                score += 0.75
            elif candidate["context"] and acquired["contexts"]:
                score -= 0.50
        available.append((score, -index, candidate, basis, evidence, confidence, uncertainty))
    if not available:
        return None
    _, _, selected, basis, evidence, confidence, uncertainty = max(available, key=lambda row: (row[0], row[1]))
    proposal = deepcopy(selected)
    proposal.update({
        "kind": "commitment_action_proposal", "basis": basis,
        "evidence": evidence, "confidence": confidence,
        "uncertainty": uncertainty, "execution": "external",
    })
    return proposal


def remove_evidence(state, evidence_id):
    """Remove retained evidence and recompute revisable preferences/commitments."""
    validate(state)
    evidence_id = _text(evidence_id, "evidence_id")
    if not any(item["evidence_id"] == evidence_id for item in state["evidence"]):
        raise ValueError("F11 evidence is not retained")
    state["evidence"] = [item for item in state["evidence"] if item["evidence_id"] != evidence_id]
    state["seen_evidence"] = [item for item in state["seen_evidence"] if item["evidence_id"] != evidence_id]
    state["acquired_preferences"], state["commitments"] = _derive(state)
    state["last_update"] = []
    _refresh_summary_links(state)
    _record_history(state, "removal", evidence_id)
    validate(state)
    return {"changed": True, "removed": True, "evidence_id": evidence_id, "state": deepcopy(state)}


def correct_evidence(state, evidence_id, replacement):
    """Replace one retained event with a corrected same-ID public event."""
    validate(state)
    evidence_id = _text(evidence_id, "evidence_id")
    replacement = _canonical_event(replacement)
    if replacement["evidence_id"] != evidence_id:
        raise ValueError("F11 corrections must preserve evidence identity")
    if replacement["owner"] != state["owner"] or replacement["run_id"] != state["run_id"]:
        raise ValueError("Foreign F11 correction")
    index = next((i for i, item in enumerate(state["evidence"]) if item["evidence_id"] == evidence_id), None)
    if index is None:
        raise ValueError("F11 evidence is not retained")
    if state["evidence"][index] == replacement:
        return {"changed": False, "evidence_id": evidence_id, "state": deepcopy(state)}
    state["evidence"][index] = replacement
    for i, item in enumerate(state["seen_evidence"]):
        if item["evidence_id"] == evidence_id:
            state["seen_evidence"][i] = deepcopy(replacement)
            break
    state["acquired_preferences"], state["commitments"] = _derive(state)
    state["last_update"] = [evidence_id]
    _record_history(state, "correction", evidence_id)
    validate(state)
    return {"changed": True, "evidence_id": evidence_id, "state": deepcopy(state)}


__all__ = [
    "RULE", "MAX_EVIDENCE", "MAX_SEEN_EVIDENCE", "MAX_COMMITMENTS", "MAX_SUMMARY_CLAIMS",
    "initial", "validate", "observe_event", "revise_summary", "choose_commitment_action",
    "remove_evidence", "correct_evidence",
]
