import unittest

from underworld import others_f7 as f7


def observation(observer="agent-1", target="agent-2", cues=None, reports=None):
    return {
        "observer": observer,
        "target": target,
        "visible_cues": [] if cues is None else cues,
        "social_reports": [] if reports is None else reports,
    }


def cue(source, name, strength=1.0):
    return {"source_event_id": source, "cue": name, "strength": strength}


def report(source, kind, strength=1.0):
    return {"source_event_id": source, "kind": kind, "strength": strength}


class OthersF7Tests(unittest.TestCase):
    def test_inference_is_directional(self):
        forward = f7.initial("agent-1", "agent-2")
        reverse = f7.initial("agent-2", "agent-1")
        f7.infer(forward, observation(cues=[cue("v-1", "thirst_signal")]))
        self.assertTrue(forward["estimates"]["needs"])
        self.assertEqual(reverse["evidence"], [])
        self.assertEqual(reverse["estimates"], {"needs": {}, "goals": {}, "affect": {}})

    def test_private_state_is_rejected_and_not_leaked(self):
        state = f7.initial("agent-1", "agent-2")
        private = observation(cues=[{
            "source_event_id": "v-private",
            "cue": "thirst_signal",
            "strength": 1.0,
            "target_private_mood": -1,
        }])
        with self.assertRaisesRegex(ValueError, "public fields"):
            f7.infer(state, private)
        self.assertEqual(state["evidence"], [])

        private_observation = observation()
        private_observation["target_private_goals"] = ["seek_water"]
        with self.assertRaisesRegex(ValueError, "public observation"):
            f7.infer(state, private_observation)

    def test_same_public_cues_are_deterministic(self):
        cues = [cue("v-2", "thirst_signal", 0.8), cue("v-1", "seeking_shelter", 0.6)]
        reports = [report("s-1", "asked_for_help", 0.7)]
        left = f7.infer(f7.initial("agent-1", "agent-2"), observation(cues=cues, reports=reports))
        right = f7.infer(f7.initial("agent-1", "agent-2"), observation(cues=list(reversed(cues)), reports=reports))
        self.assertEqual(left, right)
        self.assertEqual(left["estimates"], right["estimates"])
        self.assertEqual(left["estimates"]["needs"]["water"]["provenance"], ["v-2"])

    def test_ambiguous_cue_is_low_confidence_not_a_fabricated_label(self):
        result = f7.infer(f7.initial("agent-1", "agent-2"), observation(cues=[cue("v-amb", "ambiguous_stillness")]))
        self.assertEqual(result["ambiguities"], ["v-amb"])
        self.assertTrue(result["estimates"]["needs"])
        self.assertTrue(all(item["confidence"] < 0.5 for dimension in result["estimates"].values() for item in dimension.values()))
        self.assertNotIn("private_mood", result["estimates"]["affect"])

    def test_new_evidence_corrects_an_earlier_inference_and_links_sources(self):
        state = f7.initial("agent-1", "agent-2")
        first = f7.infer(state, observation(cues=[cue("v-thirst", "thirst_signal")]))
        before = first["estimates"]["needs"]["water"]
        second = f7.infer(state, observation(cues=[cue("v-drink", "drinking_observed")]))
        after = second["estimates"]["needs"]["water"]
        self.assertGreater(before["belief"], 0)
        self.assertLess(after["belief"], before["belief"])
        self.assertEqual(after["provenance"], ["v-drink", "v-thirst"])
        self.assertTrue(second["correction"]["applied"])
        self.assertEqual(second["correction"]["source_event_ids"], ["v-drink"])

    def test_operator_label_manipulation_does_not_change_inference(self):
        public = observation(cues=[cue("v-1", "hunger_signal")], reports=[report("s-1", "asked_for_food")])
        first = f7.infer(f7.initial("agent-1", "agent-2"), public, operator_label="urgent-danger")
        second = f7.infer(f7.initial("agent-1", "agent-2"), public, operator_label="friendly-and-safe")
        self.assertEqual(first, second)

    def test_evidence_and_hypotheses_are_finite_and_duplicate_ids_are_rejected(self):
        state = f7.initial("agent-1", "agent-2")
        too_many = observation(cues=[cue(f"v-{index}", "calm_posture") for index in range(f7.MAX_EVIDENCE + 1)])
        with self.assertRaisesRegex(ValueError, "batch is too large"):
            f7.infer(state, too_many)
        first = f7.infer(state, observation(cues=[cue("v-1", "calm_posture")]))
        self.assertEqual(len(first["evidence"]), 1)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            f7.infer(state, observation(cues=[cue("v-1", "calm_posture")]))


if __name__ == "__main__":
    unittest.main()
