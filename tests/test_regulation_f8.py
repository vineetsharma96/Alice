import copy
import json
import unittest

from underworld import regulation_f8 as regulation


def observation(stress=0.1, fear=0.1, hunger=0.1, fatigue=0.1, tick=0):
    return {
        "agent_id": "alice",
        "run_id": "run-1",
        "tick": tick,
        "dt_s": 2.0,
        "own_state": {
            "alive": True,
            "present": True,
            "affect": {"stress": stress, "fear": fear},
            "body": {"health": 1.0, "injury": 0.0, "hunger": hunger,
                     "thirst": 0.1, "fatigue": fatigue},
            "weather": {"cold_burden": 0.0, "wetness": 0.0},
        },
    }


def candidate(strategy, cost=1.0, duration=2.0):
    actions = {
        "rest": ("rest", {"seconds": duration}),
        "move_to_safety": ("move", {"destination": "shelter"}),
        "request_help": ("request_help", {"reason": "safety"}),
        "reconsider": ("reconsider", {"reason": "review"}),
        "switch_plan": ("switch_plan", {"plan": "fallback"}),
    }
    action_type, parameters = actions[strategy]
    return {"strategy": strategy, "action_type": action_type,
            "parameters": parameters, "requested_duration": duration,
            "estimated_cost_s": cost}


def outcome(request_id, strategy="rest", status="completed", cost=3.0):
    action_type = {"rest": "rest", "move_to_safety": "move",
                   "request_help": "request_help", "reconsider": "reconsider",
                   "switch_plan": "switch_plan"}[strategy]
    return {"request_id": request_id, "status": status,
            "action_type": action_type, "strategy": strategy, "result": {},
            "estimated_cost_s": cost}


class RegulationF8Tests(unittest.TestCase):
    def setUp(self):
        self.state = regulation.initial("alice", "run-1")

    def test_gradual_learned_efficacy_and_bounded_evidence(self):
        before = observation(stress=0.7, tick=0)
        after = observation(stress=0.2, tick=5)
        first = regulation.observe_outcome(self.state, before, after, outcome("r1"))
        self.assertEqual(first["elapsed_s"], 10.0)
        value1 = self.state["efficacy"]["rest"]["strained"]["value"]
        regulation.observe_outcome(self.state, before, after, outcome("r2"))
        value2 = self.state["efficacy"]["rest"]["strained"]["value"]
        self.assertGreater(value1, 0.5)
        self.assertGreater(value2, value1)
        self.assertLess(value1, 1.0)
        self.assertLessEqual(len(self.state["evidence"]), 32)

    def test_context_separation(self):
        calm = observation(stress=0.05, fear=0.05)
        danger = observation(stress=0.95, fear=0.95)
        self.assertEqual(regulation.context(calm), "calm")
        self.assertEqual(regulation.context(danger), "danger")
        regulation.observe_outcome(self.state, calm, observation(tick=2), outcome("calm-1"))
        self.assertEqual(self.state["efficacy"]["rest"]["calm"]["attempts"], 1)
        self.assertEqual(self.state["efficacy"]["rest"]["danger"]["attempts"], 0)

    def test_repeated_failures_switch_selection(self):
        before = observation(stress=0.6, tick=0)
        after = observation(stress=0.8, tick=1)
        for index in range(4):
            regulation.observe_outcome(self.state, before, after,
                                       outcome(f"fail-{index}", status="failed"))
        selected = regulation.choose(before, self.state,
                                     [candidate("rest"), candidate("switch_plan")])
        self.assertEqual(selected["strategy"], "switch_plan")
        self.assertGreater(self.state["failure_streaks"]["rest"], 0)

    def test_danger_avoids_unsafe_strategy(self):
        danger = observation(stress=0.95, fear=0.95)
        selected = regulation.choose(danger, self.state,
                                     [candidate("rest"), candidate("reconsider"),
                                      candidate("move_to_safety")])
        self.assertEqual(selected["strategy"], "move_to_safety")
        self.assertIsNone(regulation.choose(danger, self.state, [candidate("rest")]))

    def test_cost_time_and_body_burden_are_recorded(self):
        before = observation(hunger=0.8, tick=4)
        after = observation(hunger=0.3, tick=9)
        evidence = regulation.observe_outcome(self.state, before, after,
                                              outcome("cost-1", cost=7.5))
        stats = self.state["efficacy"]["rest"]["depleted"]
        self.assertEqual(evidence["elapsed_s"], 10.0)
        self.assertEqual(evidence["cost_s"], 7.5)
        self.assertGreater(evidence["burden_before"], evidence["burden_after"])
        self.assertEqual(stats["elapsed_s"], 10.0)
        self.assertEqual(stats["cost_s"], 7.5)

    def test_malformed_and_private_fields_rejected(self):
        bad = candidate("rest")
        bad["private_state"] = {"stress": 0}
        with self.assertRaises(ValueError):
            regulation.choose(observation(), self.state, [bad])
        private_observation = observation()
        private_observation["other_state"] = {"stress": 1}
        with self.assertRaises(ValueError):
            regulation.context(private_observation)
        bad_outcome = outcome("bad")
        bad_outcome["target_private_mood"] = 1
        with self.assertRaises(ValueError):
            regulation.observe_outcome(self.state, observation(), observation(tick=1), bad_outcome)

    def test_duplicate_evidence_and_json_copy_are_pure(self):
        before = observation(stress=0.7)
        after = observation(stress=0.2, tick=2)
        original_before = copy.deepcopy(before)
        original_after = copy.deepcopy(after)
        regulation.observe_outcome(self.state, before, after, outcome("same"))
        snapshot = json.loads(json.dumps(self.state))
        self.assertIsNone(regulation.observe_outcome(self.state, before, after, outcome("same")))
        self.assertEqual(self.state, snapshot)
        self.assertEqual(before, original_before)
        self.assertEqual(after, original_after)
        regulation.validate(json.loads(json.dumps(self.state)))


if __name__ == "__main__":
    unittest.main()
