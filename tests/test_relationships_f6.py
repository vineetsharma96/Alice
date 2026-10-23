import json
import unittest

from underworld import relationships_f6 as relationships


def event(observer, other, kind, seq, tick):
    return {"observer": observer, "other": other, "kind": kind,
            "source_event_seq": str(seq), "tick": tick}


class RelationshipF6Tests(unittest.TestCase):
    def test_directional_familiarity_without_automatic_trust(self):
        ab = relationships.initial("agent-1", "agent-2")
        ba = relationships.initial("agent-2", "agent-1")
        relationships.observe(ab, event("agent-1", "agent-2", "heard", 1, 4))
        self.assertGreater(ab["familiarity"], 0)
        self.assertEqual(ab["trust"], 0)
        self.assertEqual(ba["observations"], 0)

    def test_witnessed_outcomes_update_only_the_observer_and_repair(self):
        ab = relationships.initial("agent-1", "agent-2")
        relationships.observe(ab, event("agent-1", "agent-2", "task_failed", 2, 8))
        damaged = ab["trust"]
        relationships.observe(ab, event("agent-1", "agent-2", "task_completed", 3, 12))
        relationships.observe(ab, event("agent-1", "agent-2", "task_completed", 4, 16))
        self.assertGreater(ab["trust"], damaged)
        self.assertGreater(ab["reliability"], 0)
        self.assertEqual(ab["evidence"], [
            {"source_event_seq": "2", "kind": "task_failed", "tick": 8},
            {"source_event_seq": "3", "kind": "task_completed", "tick": 12},
            {"source_event_seq": "4", "kind": "task_completed", "tick": 16},
        ])

    def test_one_interaction_does_not_create_attachment_and_duplicate_is_idempotent(self):
        ab = relationships.initial("agent-1", "agent-2")
        relationships.observe(ab, event("agent-1", "agent-2", "shared_activity", 5, 20))
        before = json.loads(json.dumps(ab))
        self.assertEqual(ab["attachment"], 0)
        self.assertIsNone(relationships.observe(ab, event("agent-1", "agent-2", "shared_activity", 5, 20)))
        self.assertEqual(ab, before)

    def test_helper_choice_is_directional_bounded_and_deterministic(self):
        trusted = relationships.initial("agent-1", "agent-2")
        unknown = relationships.initial("agent-1", "agent-3")
        for seq in range(10, 13):
            relationships.observe(trusted, event("agent-1", "agent-2", "task_completed", seq, seq))
        choice = relationships.choose_helper({"agent-2": trusted, "agent-3": unknown}, ["agent-3", "agent-2"])
        self.assertIsNotNone(choice)
        assert choice is not None
        self.assertEqual(choice["other"], "agent-2")
        self.assertLessEqual(choice["score"], 1)
        self.assertIn("native feasibility", choice["origin"])

    def test_private_target_state_is_rejected(self):
        ab = relationships.initial("agent-1", "agent-2")
        private_event = event("agent-1", "agent-2", "task_completed", 20, 40)
        private_event["target_private_mood"] = -1
        with self.assertRaisesRegex(ValueError, "private target state"):
            relationships.observe(ab, private_event)


if __name__ == "__main__":
    unittest.main()
