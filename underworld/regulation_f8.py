"""Pure, bounded F8 emotional-regulation policy learning.

This slice is deliberately an overlay: it consumes an inhabitant's own
observations and native-shaped action receipts, and returns copy-friendly
Python data.  It never owns a world, database, model, other-agent state, or
native mutation capability.
"""

from copy import deepcopy
import math


RULE = "alice-regulation-f8-1"
MAX_EVIDENCE = 32
MAX_ID_LENGTH = 128
MAX_CANDIDATES = 32

STRATEGIES = (
    "rest",
    "move_to_safety",
    "request_help",
    "reconsider",
    "switch_plan",
)
CONTEXTS = ("calm", "strained", "danger", "depleted", "uncertain")
SAFE_IN_DANGER = frozenset(("move_to_safety", "request_help"))
ACTION_TYPES = {
    "rest": "rest",
    "move_to_safety": "move",
    "request_help": "request_help",
    "reconsider": "reconsider",
    "switch_plan": "switch_plan",
}
PARAMETERS = {
    "rest": frozenset(("seconds",)),
    "move": frozenset(("target", "target_position", "destination", "shelter_id")),
    "request_help": frozenset(("recipient", "reason", "message")),
    "reconsider": frozenset(("reason",)),
    "switch_plan": frozenset(("plan", "reason")),
}
STAT_KEYS = frozenset({
    "attempts", "successes", "failures", "failure_streak", "value",
    "uncertainty", "elapsed_s", "cost_s",
})


def _text(value, label):
    if type(value) is not str or not value or len(value) > MAX_ID_LENGTH:
        raise ValueError(f"Invalid F8 {label}")
    return value


def _number(value, label, low=0.0, high=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"Invalid F8 {label}")
    value = float(value)
    if value < low or (high is not None and value > high):
        raise ValueError(f"Invalid F8 {label}")
    return value


def _reject_private_keys(value, label="value"):
    """Reject common private-state/transport escape hatches recursively."""
    if isinstance(value, dict):
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"Invalid F8 {label} field")
            lowered = key.lower()
            if any(token in lowered for token in (
                    "private", "secret", "hidden", "other_agent", "other_state",
                    "target_state", "llm", "model_prompt")):
                raise ValueError("F8 private fields are not accepted")
            _reject_private_keys(item, f"{label}.{key}")
    elif isinstance(value, list):
        for item in value:
            _reject_private_keys(item, label)


def _observation(observation):
    if type(observation) is not dict:
        raise ValueError("F8 observation must be a mapping")
    observation = deepcopy(observation)
    _reject_private_keys(observation, "observation")
    required = {"agent_id", "run_id", "tick", "dt_s", "own_state"}
    if not required.issubset(observation) or not isinstance(observation["own_state"], dict):
        raise ValueError("F8 observation needs own identity, time, and own_state")
    if type(observation["tick"]) is str and observation["tick"].isdigit():
        observation["tick"] = int(observation["tick"])
    if type(observation["tick"]) is not int or observation["tick"] < 0:
        raise ValueError("Invalid F8 observation tick")
    _number(observation["dt_s"], "observation dt_s", 0.0, 3600.0)
    _text(observation["agent_id"], "observation owner")
    _text(observation["run_id"], "observation run")
    own = observation["own_state"]
    for key in ("body", "weather"):
        if key in own and type(own[key]) is not dict:
            raise ValueError(f"Invalid F8 own_state {key}")
    for key in ("affect",):
        if key in own and type(own[key]) is not dict:
            raise ValueError(f"Invalid F8 own_state {key}")
    return observation


def _signal(observation):
    observation = _observation(observation)
    own = observation["own_state"]
    body = own.get("body", {})
    weather = own.get("weather", {})
    affect = own.get("affect", {})

    def read(mapping, names, default=0.0):
        for name in names:
            if name in mapping:
                return _number(mapping[name], name, 0.0, 1.0)
        return default

    stress = read(own, ("stress",), read(affect, ("stress",), 0.0))
    fear = read(own, ("fear",), read(affect, ("fear",), 0.0))
    hunger = read(body, ("hunger",), 0.0)
    thirst = read(body, ("thirst",), 0.0)
    fatigue = read(body, ("fatigue", "exhaustion"), 0.0)
    injury = read(body, ("injury",), 0.0)
    health = read(body, ("health",), 1.0)
    cold = read(weather, ("cold_burden", "thermal"), 0.0)
    wetness = read(weather, ("wetness",), 0.0)
    resource_burden = max(hunger, thirst, fatigue)
    body_burden = max(injury, 1.0 - health, cold, wetness)
    burden = max(resource_burden, body_burden, stress, fear)
    explicit_danger = own.get("danger", False)
    if type(explicit_danger) is not bool:
        raise ValueError("Invalid F8 danger signal")
    danger = bool(explicit_danger or not own.get("alive", True) or
                  not own.get("present", True) or injury >= 0.55 or
                  1.0 - health >= 0.55 or cold >= 0.85 or fear >= 0.85 or
                  stress >= 0.92)
    return {
        "stress": stress, "fear": fear, "resource_burden": resource_burden,
        "body_burden": body_burden, "burden": burden, "danger": danger,
        "tick": observation["tick"], "dt_s": float(observation["dt_s"]),
    }


def initial(owner, run_id):
    """Return an empty, authored F8 learner for one owner/run pair."""
    owner, run_id = _text(owner, "owner"), _text(run_id, "run_id")
    efficacy = {}
    for strategy in STRATEGIES:
        efficacy[strategy] = {}
        for context_name in CONTEXTS:
            efficacy[strategy][context_name] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "failure_streak": 0,
                "value": 0.5,
                "uncertainty": 1.0,
                "elapsed_s": 0.0,
                "cost_s": 0.0,
            }
    return {
        "rule": RULE,
        "owner": owner,
        "run_id": run_id,
        "revision": 0,
        "efficacy": efficacy,
        "failure_streaks": {strategy: 0 for strategy in STRATEGIES},
        "evidence": [],
        "last_context": None,
        "last_request_id": None,
        "origin": "authored finite strategies learned from own observations and native receipts",
    }


def validate(state):
    expected = {
        "rule", "owner", "run_id", "revision", "efficacy", "failure_streaks",
        "evidence", "last_context", "last_request_id", "origin",
    }
    if type(state) is not dict or set(state) != expected or state["rule"] != RULE:
        raise ValueError("Unsupported F8 regulation schema")
    _text(state["owner"], "owner")
    _text(state["run_id"], "run_id")
    if type(state["revision"]) is not int or state["revision"] < 0:
        raise ValueError("Invalid F8 revision")
    if set(state["efficacy"]) != set(STRATEGIES):
        raise ValueError("Invalid F8 strategy set")
    if set(state["failure_streaks"]) != set(STRATEGIES):
        raise ValueError("Invalid F8 failure streak set")
    for strategy in STRATEGIES:
        streak = state["failure_streaks"][strategy]
        if type(streak) is not int or streak < 0:
            raise ValueError("Invalid F8 failure streak")
        if set(state["efficacy"][strategy]) != set(CONTEXTS):
            raise ValueError("Invalid F8 context efficacy set")
        for context_name in CONTEXTS:
            stats = state["efficacy"][strategy][context_name]
            if type(stats) is not dict or set(stats) != STAT_KEYS:
                raise ValueError("Invalid F8 efficacy record")
            for key in ("attempts", "successes", "failures", "failure_streak"):
                if type(stats[key]) is not int or stats[key] < 0:
                    raise ValueError("Invalid F8 efficacy counter")
            if stats["successes"] + stats["failures"] > stats["attempts"]:
                raise ValueError("F8 outcome counters exceed attempts")
            _number(stats["value"], "efficacy value", 0.0, 1.0)
            _number(stats["uncertainty"], "efficacy uncertainty", 0.0, 1.0)
            _number(stats["elapsed_s"], "efficacy elapsed_s", 0.0)
            _number(stats["cost_s"], "efficacy cost_s", 0.0)
    if type(state["evidence"]) is not list or len(state["evidence"]) > MAX_EVIDENCE:
        raise ValueError("F8 evidence bound exceeded")
    evidence_ids = []
    for item in state["evidence"]:
        expected_evidence = {
            "request_id", "strategy", "context", "status", "elapsed_s", "cost_s",
            "burden_before", "burden_after", "outcome_score", "failure_streak",
        }
        if type(item) is not dict or set(item) != expected_evidence:
            raise ValueError("Invalid F8 evidence")
        _text(item["request_id"], "evidence request_id")
        if item["strategy"] not in STRATEGIES or item["context"] not in CONTEXTS:
            raise ValueError("Invalid F8 evidence strategy/context")
        if item["status"] not in {"completed", "failed", "rejected", "expired"}:
            raise ValueError("Invalid F8 evidence status")
        for key in ("elapsed_s", "cost_s", "burden_before", "burden_after"):
            _number(item[key], f"evidence {key}", 0.0)
        _number(item["outcome_score"], "evidence outcome_score", 0.0, 1.0)
        if type(item["failure_streak"]) is not int or item["failure_streak"] < 0:
            raise ValueError("Invalid F8 evidence failure streak")
        evidence_ids.append(item["request_id"])
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Duplicate F8 evidence")
    if state["last_context"] is not None and state["last_context"] not in CONTEXTS:
        raise ValueError("Invalid F8 last context")
    if state["last_request_id"] is not None:
        _text(state["last_request_id"], "last request_id")
        if state["last_request_id"] not in evidence_ids:
            raise ValueError("F8 last request is not retained evidence")
    _text(state["origin"], "origin")
    return state


def context(observation):
    """Classify an own observation into one authored finite context."""
    signal = _signal(observation)
    if signal["danger"]:
        return "danger"
    if signal["resource_burden"] >= 0.6:
        return "depleted"
    if signal["burden"] >= 0.45 or signal["stress"] >= 0.45 or signal["fear"] >= 0.45:
        return "strained"
    if signal["burden"] <= 0.12:
        return "calm"
    return "uncertain"


def _candidate(candidate):
    if type(candidate) is not dict:
        raise ValueError("F8 candidates must be mappings")
    _reject_private_keys(candidate, "candidate")
    expected = {"strategy", "action_type", "parameters", "requested_duration", "estimated_cost_s"}
    if set(candidate) != expected:
        raise ValueError("Malformed F8 candidate")
    strategy = candidate["strategy"]
    if strategy not in STRATEGIES or candidate["action_type"] != ACTION_TYPES[strategy]:
        raise ValueError("Unsupported F8 strategy/action contract")
    if type(candidate["parameters"]) is not dict:
        raise ValueError("F8 candidate parameters must be a mapping")
    if not set(candidate["parameters"]).issubset(PARAMETERS[candidate["action_type"]]):
        raise ValueError("F8 candidate contains an unsupported parameter")
    for key, value in candidate["parameters"].items():
        if type(key) is not str:
            raise ValueError("Invalid F8 candidate parameter")
        if type(value) not in (str, int, float, bool, list, tuple):
            raise ValueError("Invalid F8 candidate parameter value")
        if isinstance(value, (list, tuple)) and len(value) > 16:
            raise ValueError("F8 candidate parameter is too large")
        def finite_parameter(item):
            if isinstance(item, (list, tuple)):
                if len(item)>16:raise ValueError('F8 candidate parameter is too large')
                for child in item:finite_parameter(child)
            elif type(item) in (int,float):
                if not math.isfinite(item):raise ValueError('Nonfinite F8 parameter')
            elif type(item) not in (str,bool):
                raise ValueError('Invalid F8 nested parameter')
        finite_parameter(value)
    _number(candidate["requested_duration"], "requested_duration", 0.0, 86400.0)
    _number(candidate["estimated_cost_s"], "estimated_cost_s", 0.0, 86400.0)
    return deepcopy(candidate)


def choose(observation, state, candidates):
    """Choose a feasible authored proposal without changing state or observations."""
    validate(state)
    observation = _observation(observation)
    if observation["agent_id"] != state["owner"] or observation["run_id"] != state["run_id"]:
        raise ValueError("Foreign F8 observation")
    if type(candidates) is not list or not candidates or len(candidates) > MAX_CANDIDATES:
        raise ValueError("F8 candidates must be a non-empty bounded list")
    parsed = [_candidate(item) for item in candidates]
    context_name = context(observation)
    allowed = [item for item in parsed if context_name != "danger" or item["strategy"] in SAFE_IN_DANGER]
    if not allowed:
        return None

    def score(item):
        stats = state["efficacy"][item["strategy"]][context_name]
        exploration = 0.12 * stats["uncertainty"]
        cost_penalty = min(0.25, (item["estimated_cost_s"] + item["requested_duration"] * 0.05) / 3600.0)
        danger_bonus = 0.35 if context_name == "danger" and item["strategy"] in SAFE_IN_DANGER else 0.0
        return stats["value"] + exploration + danger_bonus - cost_penalty

    # Stable tie-breaking preserves authored candidate order while still being deterministic.
    selected = max(enumerate(allowed), key=lambda pair: (score(pair[1]), -pair[0]))[1]
    return deepcopy(selected)


def _receipt(outcome):
    """Normalize a direct native result or a receipt/result envelope."""
    if type(outcome) is not dict:
        raise ValueError("F8 outcome must be a native-shaped mapping")
    _reject_private_keys(outcome, "outcome")
    if "receipt" in outcome:
        if set(outcome) != {"strategy", "receipt", "result", "estimated_cost_s"}:
            raise ValueError("Malformed F8 receipt/result envelope")
        receipt = outcome["receipt"]
        if type(receipt) is not dict or not set(receipt).issubset({"request_id", "status", "action_type", "error_code"}):
            raise ValueError("Malformed F8 native receipt")
        if not {"request_id", "status", "action_type"}.issubset(receipt):
            raise ValueError("Incomplete F8 native receipt")
        result = outcome["result"]
        strategy = outcome["strategy"]
        estimated_cost = outcome["estimated_cost_s"]
    else:
        allowed = {"request_id", "status", "action_type", "strategy", "result", "error_code", "estimated_cost_s"}
        if not set(outcome).issubset(allowed) or not {"request_id", "status", "action_type", "result"}.issubset(outcome):
            raise ValueError("Malformed F8 native result envelope")
        receipt = {key: outcome[key] for key in ("request_id", "status", "action_type") if key in outcome}
        if "error_code" in outcome:
            receipt["error_code"] = outcome["error_code"]
        result = outcome["result"]
        strategy = outcome.get("strategy")
        estimated_cost = outcome.get("estimated_cost_s", 0.0)
    _text(receipt["request_id"], "receipt request_id")
    if receipt["status"] not in {"completed", "failed", "rejected", "expired"}:
        raise ValueError("Invalid F8 receipt status")
    _text(receipt["action_type"], "receipt action_type")
    if type(result) is not dict:
        raise ValueError("F8 result must be a mapping")
    _number(estimated_cost, "outcome estimated_cost_s", 0.0, 86400.0)
    if strategy is None:
        matches = [name for name, action in ACTION_TYPES.items() if action == receipt["action_type"]]
        if len(matches) != 1:
            raise ValueError("F8 outcome needs a strategy")
        strategy = matches[0]
    if strategy not in STRATEGIES or ACTION_TYPES[strategy] != receipt["action_type"]:
        raise ValueError("F8 outcome strategy/action mismatch")
    return receipt, result, strategy, float(estimated_cost)


def observe_outcome(state, before, after, outcome):
    """Learn one idempotent strategy outcome from own observations and a receipt."""
    validate(state)
    before = _observation(before)
    after = _observation(after)
    if (before["agent_id"], before["run_id"]) != (state["owner"], state["run_id"]):
        raise ValueError("Foreign F8 before observation")
    if (after["agent_id"], after["run_id"]) != (state["owner"], state["run_id"]):
        raise ValueError("Foreign F8 after observation")
    if after["tick"] < before["tick"]:
        raise ValueError("F8 observations move backward in time")
    receipt, result, strategy, estimated_cost = _receipt(outcome)
    request_id = receipt["request_id"]
    if any(item["request_id"] == request_id for item in state["evidence"]):
        return None

    before_signal = _signal(before)
    after_signal = _signal(after)
    elapsed_s = (after["tick"] - before["tick"]) * before_signal["dt_s"]
    status = receipt["status"]
    completed = status == "completed"
    relief = max(0.0, before_signal["burden"] - after_signal["burden"])
    harm = max(0.0, after_signal["burden"] - before_signal["burden"])
    danger_preserved = before_signal["danger"] and not after_signal["danger"]
    # Receipt completion is necessary but not sufficient: observed burden and danger changes count.
    # Completion is only a receipt fact.  Useful regulation requires observed
    # burden relief or danger resolution; an unchanged completed action stays
    # below the success threshold instead of teaching a free reset.
    target = (0.30 if completed else 0.12) + 0.42 * min(1.0, relief) + 0.10 * (1.0 if danger_preserved else 0.0)
    target -= 0.35 * min(1.0, harm)
    if completed and before_signal["danger"] and after_signal["danger"]:
        target -= 0.15
    target = max(0.0, min(1.0, target))
    context_name = context(before)
    stats = state["efficacy"][strategy][context_name]
    prior = stats["value"]
    attempts = stats["attempts"]
    alpha = 1.0 / (attempts + 2.0)
    stats["attempts"] += 1
    if target >= 0.5:
        stats["successes"] += 1
        stats["failure_streak"] = 0
        state["failure_streaks"][strategy] = 0
    else:
        stats["failures"] += 1
        stats["failure_streak"] += 1
        state["failure_streaks"][strategy] += 1
    stats["value"] = max(0.0, min(1.0, prior + alpha * (target - prior)))
    stats["uncertainty"] = 1.0 / math.sqrt(stats["attempts"] + 1.0)
    stats["elapsed_s"] += elapsed_s
    stats["cost_s"] += estimated_cost
    evidence = {
        "request_id": request_id,
        "strategy": strategy,
        "context": context_name,
        "status": status,
        "elapsed_s": elapsed_s,
        "cost_s": estimated_cost,
        "burden_before": before_signal["burden"],
        "burden_after": after_signal["burden"],
        "outcome_score": target,
        "failure_streak": stats["failure_streak"],
    }
    state["evidence"] = (state["evidence"] + [evidence])[-MAX_EVIDENCE:]
    state["revision"] += 1
    state["last_context"] = context_name
    state["last_request_id"] = request_id
    validate(state)
    return deepcopy(evidence)


__all__ = [
    "RULE", "MAX_EVIDENCE", "STRATEGIES", "CONTEXTS", "initial", "validate",
    "context", "choose", "observe_outcome",
]
