"""Pure, bounded F9 emotional communication learning.

F9 is an additive offline overlay.  Each agent owns its own production and
comprehension associations; a token is only a channel identifier until public
feedback gives a receiver evidence about its meaning.  Returned messages and
assistance choices are delivery/action proposals for an external authority.
"""

from copy import deepcopy
import hashlib
import math
import re


RULE = "alice-communication-f9-1"
MAX_EVIDENCE = 32
MAX_SEEN_EVIDENCE = 256
MAX_ASSOCIATION_EVIDENCE = 8
MAX_CANDIDATES = 16
MAX_PARTNERS = 16
MAX_TOKENS_PER_PARTNER = 32
MAX_ID_LENGTH = 128
MAX_TOKEN_LENGTH = 32

MEANINGS = ("distress", "relief", "calm", "danger", "help")
_MEANING_SET = frozenset(MEANINGS)
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,31}$")
_FORBIDDEN_KEYS = frozenset({
    "private", "hidden", "private_state", "hidden_state", "target_state",
    "operator", "operator_label", "observer_label", "secret", "llm",
    "model", "model_prompt", "prompt", "other_agent", "foreign_state",
})


def _text(value, label):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH or not _ID_RE.fullmatch(value):
        raise ValueError(f"Invalid F9 {label}")
    return value


def _token(value):
    if type(value) is not str or not _TOKEN_RE.fullmatch(value):
        raise ValueError("Invalid F9 token")
    return value


def _meaning(value):
    if type(value) is not str or value not in _MEANING_SET:
        raise ValueError("Unknown F9 emotional meaning")
    return value


def _reject_forbidden(value, label="value"):
    """Reject private-state and model/operator transport escape hatches."""
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid F9 {label} field")
            lowered = key.lower()
            if lowered in _FORBIDDEN_KEYS or any(part in lowered for part in (
                    "target_private", "private_target", "hidden_target", "operator_", "model_")):
                raise ValueError("F9 private, hidden, operator, and model fields are not accepted")
            _reject_forbidden(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item, label)
    elif isinstance(value, tuple):
        raise ValueError(f"F9 {label} must be JSON-copyable")


def _finite_number(value, label, low=0.0, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"Invalid F9 {label}")
    value = float(value)
    if value < low or (high is not None and value > high):
        raise ValueError(f"Invalid F9 {label}")
    return value


def _new_entry():
    return {
        "scores": {meaning: 0 for meaning in MEANINGS},
        "confidence": {meaning: 0.0 for meaning in MEANINGS},
        "uncertainty": 1.0,
        "exposures": 0,
        "successes": 0,
        "failures": 0,
        "evidence": [],
    }


def _recompute(entry):
    positive = {meaning: max(0, int(entry["scores"][meaning])) for meaning in MEANINGS}
    total = sum(positive.values())
    if total:
        entry["confidence"] = {
            meaning: round(positive[meaning] / float(total + 1), 6)
            for meaning in MEANINGS
        }
        entry["uncertainty"] = round(1.0 - max(entry["confidence"].values()), 6)
    else:
        entry["confidence"] = {meaning: 0.0 for meaning in MEANINGS}
        entry["uncertainty"] = 1.0


def _partner_uncertainty(exposures):
    return round(1.0 / math.sqrt(float(exposures) + 1.0), 6)


def _interpret(state, speaker, token):
    _text(speaker, "speaker")
    _token(token)
    entry = state["comprehension"].get(speaker, {}).get(token)
    if entry is None:
        return {"meaning": None, "confidence": 0.0, "uncertainty": 1.0,
                "scores": {meaning: 0 for meaning in MEANINGS}}
    best_score = max(entry["scores"].values())
    best = [meaning for meaning in MEANINGS if entry["scores"][meaning] == best_score and best_score > 0]
    meaning = sorted(best)[0] if len(best) == 1 else None
    confidence = entry["confidence"][meaning] if meaning is not None else 0.0
    partner = state["partner_uncertainty"].get(speaker, {"exposures": 0, "uncertainty": 1.0})
    uncertainty = max(float(entry["uncertainty"]), float(partner["uncertainty"]))
    return {"meaning": meaning, "confidence": round(confidence, 6),
            "uncertainty": round(uncertainty, 6), "scores": dict(entry["scores"])}


def _find_evidence(state, evidence_id):
    return next((item for item in state["seen_evidence"] if item["evidence_id"] == evidence_id), None)


def _record(state, event):
    state["evidence"] = (state["evidence"] + [event])[-MAX_EVIDENCE:]
    state["seen_evidence"] = (state["seen_evidence"] + [deepcopy(event)])[-MAX_SEEN_EVIDENCE:]
    state["revision"] += 1
    state["last_message"] = deepcopy(event)


def _same_or_conflict(existing, expected):
    if existing is None:
        return False
    if existing != expected:
        raise ValueError("Conflicting duplicate F9 evidence")
    return True


def _authored_token(state, meaning):
    seed = f"{state['owner']}:{state['run_id']}:{meaning}:f9-channel".encode()
    token = "sig-" + hashlib.sha256(seed).hexdigest()[:12]
    used = {entry["token"] for entry in state["production"].values()}
    if token not in used:
        return token
    for index in range(1, 100):
        candidate = "sig-" + hashlib.sha256(seed + f":{index}".encode()).hexdigest()[:12]
        if candidate not in used:
            return candidate
    raise ValueError("F9 authored channel space exhausted")


def _validate_event(item):
    if type(item) is not dict or "evidence_id" not in item or "kind" not in item:
        raise ValueError("Invalid F9 evidence")
    _text(item["evidence_id"], "evidence_id")
    if item["kind"] not in {"emission", "delivery", "public_feedback"}:
        raise ValueError("Invalid F9 evidence kind")
    if item["kind"] == "emission":
        required = {"evidence_id", "kind", "meaning", "token", "partner"}
        if set(item) != required:
            raise ValueError("Invalid F9 emission evidence")
        _meaning(item["meaning"])
        _token(item["token"])
        _text(item["partner"], "partner")
    elif item["kind"] == "delivery":
        required = {"evidence_id", "kind", "speaker", "token"}
        if set(item) != required:
            raise ValueError("Invalid F9 delivery evidence")
        _text(item["speaker"], "speaker")
        _token(item["token"])
    else:
        required = {"evidence_id", "kind", "partner", "token", "observed_meaning", "success"}
        if set(item) != required:
            raise ValueError("Invalid F9 feedback evidence")
        _text(item["partner"], "partner")
        _token(item["token"])
        _meaning(item["observed_meaning"])
        if type(item["success"]) is not bool:
            raise ValueError("Invalid F9 feedback success")


def initial(agent, run_id):
    """Return an empty private communication learner for one agent/run."""
    agent, run_id = _text(agent, "agent"), _text(run_id, "run_id")
    return {
        "rule": RULE,
        "owner": agent,
        "run_id": run_id,
        "revision": 0,
        "production": {},
        "comprehension": {},
        "partner_uncertainty": {},
        "evidence": [],
        "seen_evidence": [],
        "last_message": None,
        "origin": "authored arbitrary channels; private associations learned only from tagged public feedback",
    }


def validate(state):
    expected = {
        "rule", "owner", "run_id", "revision", "production", "comprehension",
        "partner_uncertainty", "evidence", "seen_evidence", "last_message", "origin",
    }
    if type(state) is not dict or set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F9 communication schema")
    _text(state["owner"], "owner")
    _text(state["run_id"], "run_id")
    if type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("Invalid F9 revision")
    if type(state["origin"]) is not str or not state["origin"]:
        raise ValueError("Invalid F9 origin")
    if type(state["production"]) is not dict or len(state["production"]) > len(MEANINGS):
        raise ValueError("Invalid F9 production map")
    production_tokens = []
    for meaning, entry in state["production"].items():
        _meaning(meaning)
        if type(entry) is not dict or set(entry) != {"token", "evidence"}:
            raise ValueError("Invalid F9 production association")
        _token(entry["token"])
        if entry["token"] in production_tokens:
            raise ValueError("F9 production token collision")
        production_tokens.append(entry["token"])
        if type(entry["evidence"]) is not list or len(entry["evidence"]) > MAX_ASSOCIATION_EVIDENCE:
            raise ValueError("F9 production evidence bound exceeded")
        for evidence_id in entry["evidence"]:
            _text(evidence_id, "production evidence_id")
    if type(state["comprehension"]) is not dict or len(state["comprehension"]) > MAX_PARTNERS:
        raise ValueError("Invalid F9 comprehension map")
    for partner, tokens in state["comprehension"].items():
        _text(partner, "partner")
        if partner == state["owner"] or type(tokens) is not dict or len(tokens) > MAX_TOKENS_PER_PARTNER:
            raise ValueError("Invalid F9 comprehension partner")
        for token, entry in tokens.items():
            _token(token)
            if type(entry) is not dict or set(entry) != {
                    "scores", "confidence", "uncertainty", "exposures", "successes", "failures", "evidence"}:
                raise ValueError("Invalid F9 comprehension association")
            if set(entry["scores"]) != set(MEANINGS) or set(entry["confidence"]) != set(MEANINGS):
                raise ValueError("Invalid F9 meaning score set")
            for meaning in MEANINGS:
                if type(entry["scores"][meaning]) is not int or not -MAX_EVIDENCE <= entry["scores"][meaning] <= MAX_EVIDENCE:
                    raise ValueError("Invalid F9 meaning score")
                _finite_number(entry["confidence"][meaning], "confidence", 0.0, 1.0)
            _finite_number(entry["uncertainty"], "uncertainty", 0.0, 1.0)
            expected_entry = deepcopy(entry)
            _recompute(expected_entry)
            if (entry["confidence"], entry["uncertainty"]) != (
                    expected_entry["confidence"], expected_entry["uncertainty"]):
                raise ValueError("Inconsistent F9 comprehension confidence")
            for key in ("exposures", "successes", "failures"):
                if type(entry[key]) is not int or entry[key] < 0:
                    raise ValueError("Invalid F9 comprehension count")
            if entry["successes"] + entry["failures"] > entry["exposures"]:
                raise ValueError("F9 feedback counts exceed exposures")
            if type(entry["evidence"]) is not list or len(entry["evidence"]) > MAX_ASSOCIATION_EVIDENCE:
                raise ValueError("F9 comprehension evidence bound exceeded")
            for evidence_id in entry["evidence"]:
                _text(evidence_id, "comprehension evidence_id")
    if type(state["partner_uncertainty"]) is not dict:
        raise ValueError("Invalid F9 partner uncertainty map")
    for partner, item in state["partner_uncertainty"].items():
        _text(partner, "uncertainty partner")
        if partner == state["owner"] or type(item) is not dict or set(item) != {"exposures", "uncertainty"}:
            raise ValueError("Invalid F9 partner uncertainty")
        if type(item["exposures"]) is not int or item["exposures"] < 0:
            raise ValueError("Invalid F9 partner exposures")
        _finite_number(item["uncertainty"], "partner uncertainty", 0.0, 1.0)
        if item["uncertainty"] != _partner_uncertainty(item["exposures"]):
            raise ValueError("Inconsistent F9 partner uncertainty")
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("F9 evidence bound exceeded")
    if type(state["seen_evidence"]) is not list or len(state["seen_evidence"]) > MAX_SEEN_EVIDENCE:
        raise ValueError("F9 duplicate ledger bound exceeded")
    evidence_ids = []
    for item in state["evidence"]:
        _validate_event(item)
        evidence_ids.append(item["evidence_id"])
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate F9 evidence")
    seen_ids = []
    for item in state["seen_evidence"]:
        _validate_event(item)
        seen_ids.append(item["evidence_id"])
    if len(seen_ids) != len(set(seen_ids)):
        raise ValueError("Duplicate F9 duplicate-ledger evidence")
    if any(item["evidence_id"] not in seen_ids for item in state["evidence"]):
        raise ValueError("F9 retained evidence missing from duplicate ledger")
    if state["last_message"] is not None:
        if type(state["last_message"]) is not dict or state["last_message"].get("evidence_id") not in seen_ids:
            raise ValueError("F9 last message is not retained evidence")
    return state


def emit(state, meaning, partner, evidence_id):
    """Author or reuse a private channel and return a delivery proposal."""
    validate(state)
    meaning, partner, evidence_id = _meaning(meaning), _text(partner, "partner"), _text(evidence_id, "evidence_id")
    if partner == state["owner"]:
        raise ValueError("F9 communication requires a distinct partner")
    token = state["production"].get(meaning, {}).get("token") or _authored_token(state, meaning)
    event = {"evidence_id": evidence_id, "kind": "emission", "meaning": meaning,
             "token": token, "partner": partner}
    existing = _find_evidence(state, evidence_id)
    if _same_or_conflict(existing, event):
        return {"kind": "delivery_proposal", "speaker": state["owner"], "partner": partner,
                "token": token, "evidence_id": evidence_id, "execution": "external"}
    production = state["production"].setdefault(meaning, {"token": token, "evidence": []})
    if production["token"] != token:
        raise ValueError("Conflicting F9 production association")
    production["evidence"] = (production["evidence"] + [evidence_id])[-MAX_ASSOCIATION_EVIDENCE:]
    _record(state, event)
    validate(state)
    return {"kind": "delivery_proposal", "speaker": state["owner"], "partner": partner,
            "token": token, "evidence_id": evidence_id, "execution": "external"}


def receive(state, speaker, token, evidence_id):
    """Record a delivered token without guessing its emotional meaning."""
    validate(state)
    speaker, token, evidence_id = _text(speaker, "speaker"), _token(token), _text(evidence_id, "evidence_id")
    if speaker == state["owner"]:
        raise ValueError("F9 receiver cannot receive from self")
    event = {"evidence_id": evidence_id, "kind": "delivery", "speaker": speaker, "token": token}
    existing = _find_evidence(state, evidence_id)
    if _same_or_conflict(existing, event):
        interpretation = _interpret(state, speaker, token)
    else:
        if speaker not in state["comprehension"] and len(state["comprehension"]) >= MAX_PARTNERS:
            raise ValueError("F9 partner association budget exhausted")
        if speaker in state["comprehension"] and token not in state["comprehension"][speaker] and len(state["comprehension"][speaker]) >= MAX_TOKENS_PER_PARTNER:
            raise ValueError("F9 token association budget exhausted")
        state["comprehension"].setdefault(speaker, {}).setdefault(token, _new_entry())
        partner = state["partner_uncertainty"].setdefault(speaker, {"exposures": 0, "uncertainty": 1.0})
        partner["exposures"] += 1
        partner["uncertainty"] = _partner_uncertainty(partner["exposures"])
        _record(state, event)
        interpretation = _interpret(state, speaker, token)
        validate(state)
    return {"kind": "delivery_proposal", "speaker": speaker, "receiver": state["owner"],
            "token": token, "evidence_id": evidence_id, "interpretation": interpretation,
            "execution": "external"}


def learn_from_feedback(state, token, observed_meaning, success, evidence_id, partner):
    """Apply one explicitly tagged public feedback event to one partner map."""
    validate(state)
    token, observed_meaning = _token(token), _meaning(observed_meaning)
    partner, evidence_id = _text(partner, "partner"), _text(evidence_id, "evidence_id")
    if partner == state["owner"] or type(success) is not bool:
        raise ValueError("Invalid F9 feedback identity or success")
    event = {"evidence_id": evidence_id, "kind": "public_feedback", "partner": partner,
             "token": token, "observed_meaning": observed_meaning, "success": success}
    existing = _find_evidence(state, evidence_id)
    if _same_or_conflict(existing, event):
        interpretation = _interpret(state, partner, token)
        return {"kind": "public_feedback", "source": "public_feedback", "changed": False,
                "partner": partner, "token": token, "observed_meaning": observed_meaning,
                "success": success, "interpretation": interpretation}
    if partner not in state["comprehension"] and len(state["comprehension"]) >= MAX_PARTNERS:
        raise ValueError("F9 partner association budget exhausted")
    if partner in state["comprehension"] and token not in state["comprehension"][partner] and len(state["comprehension"][partner]) >= MAX_TOKENS_PER_PARTNER:
        raise ValueError("F9 token association budget exhausted")
    entry = state["comprehension"].setdefault(partner, {}).setdefault(token, _new_entry())
    partner_stats = state["partner_uncertainty"].setdefault(partner, {"exposures": 0, "uncertainty": 1.0})
    partner_stats["exposures"] += 1
    partner_stats["uncertainty"] = _partner_uncertainty(partner_stats["exposures"])
    entry["exposures"] += 1
    if success:
        entry["scores"][observed_meaning] = min(MAX_EVIDENCE, entry["scores"][observed_meaning] + 1)
        entry["successes"] += 1
    else:
        entry["scores"][observed_meaning] = max(-MAX_EVIDENCE, entry["scores"][observed_meaning] - 1)
        entry["failures"] += 1
    entry["evidence"] = (entry["evidence"] + [evidence_id])[-MAX_ASSOCIATION_EVIDENCE:]
    _recompute(entry)
    _record(state, event)
    interpretation = _interpret(state, partner, token)
    validate(state)
    return {"kind": "public_feedback", "source": "public_feedback", "changed": True,
            "partner": partner, "token": token, "observed_meaning": observed_meaning,
            "success": success, "interpretation": interpretation}


def choose_assistance(state, observation, candidates):
    """Choose a bounded assistance proposal without executing any native action."""
    validate(state)
    if type(observation) is not dict:
        raise ValueError("F9 observation must be a mapping")
    _reject_forbidden(observation, "observation")
    allowed_observation = {"agent_id", "run_id", "heard", "signals"}
    if not set(observation).issubset(allowed_observation) or observation.get("agent_id") != state["owner"] or observation.get("run_id") != state["run_id"]:
        raise ValueError("Foreign or malformed F9 observation")
    heard = observation.get("heard")
    if heard is not None:
        if type(heard) is not dict or set(heard) != {"speaker", "token"}:
            raise ValueError("Malformed F9 heard message")
        speaker, token = _text(heard["speaker"], "heard speaker"), _token(heard["token"])
        if speaker == state["owner"]:
            raise ValueError("Foreign F9 heard speaker")
        interpretation = _interpret(state, speaker, token)
    else:
        speaker = token = None
        interpretation = {"meaning": None, "confidence": 0.0, "uncertainty": 1.0}
    if type(candidates) is not list or not candidates or len(candidates) > MAX_CANDIDATES:
        raise ValueError("F9 candidates must be a non-empty bounded list")
    parsed = []
    for candidate in candidates:
        if type(candidate) is not dict or "meaning" not in candidate:
            raise ValueError("F9 assistance candidates need a meaning")
        _reject_forbidden(candidate, "candidate")
        _meaning(candidate["meaning"])
        parsed.append(deepcopy(candidate))
    signals = observation.get("signals", {})
    if type(signals) is not dict:
        raise ValueError("F9 observation signals must be a mapping")
    for key, value in signals.items():
        _meaning(key)
        _finite_number(value, "signal", 0.0, 1.0)

    def score(item):
        meaning = item["meaning"]
        if heard is not None:
            return interpretation["scores"].get(meaning, 0)
        return float(signals.get(meaning, 0.0))

    selected_index, selected = max(enumerate(parsed), key=lambda pair: (score(pair[1]), -pair[0]))
    return {"kind": "assistance_proposal", "candidate": selected,
            "speaker": speaker, "token": token,
            "confidence": interpretation.get("confidence", 0.0) if heard is not None else 0.0,
            "uncertainty": interpretation.get("uncertainty", 1.0),
            "execution": "external"}


def interpret(state, speaker, token):
    """Return a copy of the receiver's partner-specific interpretation."""
    validate(state)
    return deepcopy(_interpret(state, speaker, token))


__all__ = [
    "RULE", "MAX_EVIDENCE", "MEANINGS", "initial", "validate", "emit",
    "receive", "learn_from_feedback", "choose_assistance", "interpret",
]
