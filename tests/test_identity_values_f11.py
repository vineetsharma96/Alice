import copy
import json
import unittest

from underworld import identity_values_f11 as values


def event(evidence_id, value="care", status="succeeded", *, context=None,
          kind="own_observation", provenance="native", owner="alice", run_id="run-1",
          outcome="completed", source=None):
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "owner": owner,
        "run_id": run_id,
        "provenance": provenance,
        "status": status,
        "value": value,
        "outcome": outcome,
        "context": list(context or []),
        "source": source or "native:" + evidence_id,
    }


class IdentityValuesF11Tests(unittest.TestCase):
    def setUp(self):
        self.state = values.initial("alice", "run-1", ["care", "craft"])

    def test_declared_values_are_separate_from_acquired_preferences(self):
        self.assertEqual(self.state["declared_values"], ["care", "craft"])
        self.assertEqual(self.state["acquired_preferences"], {})
        self.assertEqual(self.state["commitments"], {})
        values.validate(self.state)

    def test_evidence_based_revision_and_context_tags(self):
        values.observe_event(self.state, event("e1", "care", context=["shelter"]))
        self.assertIn("care", self.state["acquired_preferences"])
        self.assertEqual(self.state["acquired_preferences"]["care"]["contexts"], ["shelter"])
        values.revise_summary(self.state, {"text": "I protect nearby life", "claims": ["care"], "contexts": ["shelter"]}, "e1")
        self.assertEqual(self.state["summary"]["evidence"], ["e1"])
        self.assertEqual(self.state["revision_history"][-1]["kind"], "summary")

    def test_json_save_resume_and_varied_context_commitment_choice(self):
        values.observe_event(self.state, event("e1", "care", context=["shelter"]))
        values.observe_event(self.state, event("e2", "care", context=["shelter"]))
        saved = json.loads(json.dumps(self.state))
        values.validate(saved)
        proposal = values.choose_commitment_action(saved, {"owner": "alice", "run_id": "run-1", "context": ["shelter"]}, [
            {"action": "repair", "value": "care", "feasible": True, "owner": "alice", "run_id": "run-1"},
            {"action": "craft", "value": "craft", "feasible": True, "owner": "alice", "run_id": "run-1"},
        ])
        self.assertEqual(proposal["value"], "care")
        self.assertEqual(proposal["execution"], "external")
        self.assertEqual(saved, json.loads(json.dumps(saved)))
        other_context = values.choose_commitment_action(saved, {"owner": "alice", "run_id": "run-1", "context": ["travel"]}, [
            {"action": "craft", "value": "craft", "feasible": True, "owner": "alice", "run_id": "run-1"},
            {"action": "repair", "value": "care", "feasible": True, "owner": "alice", "run_id": "run-1"},
        ])
        self.assertEqual(other_context["value"], "care")

    def test_commitment_is_proposal_only_and_not_circular_reward(self):
        before = copy.deepcopy(self.state)
        self.assertIsNone(values.choose_commitment_action(self.state, {"owner": "alice", "run_id": "run-1", "context": []}, [
            {"action": "feel-proud", "value": "pride", "feasible": True, "owner": "alice", "run_id": "run-1"},
        ]))
        self.assertEqual(self.state, before)
        with self.assertRaises(ValueError):
            values.observe_event(self.state, event("emotion", "pride", outcome="I feel proud"))
        with self.assertRaises(ValueError):
            values.observe_event(self.state, event("report", "care", provenance="self_report"))

    def test_private_operator_model_and_foreign_fields_rejected(self):
        bad = event("bad", "care")
        bad["operator_label"] = "important"
        with self.assertRaises(ValueError):
            values.observe_event(self.state, bad)
        with self.assertRaises(ValueError):
            values.observe_event(self.state, event("foreign", owner="bob"))
        with self.assertRaises(ValueError):
            values.choose_commitment_action(self.state, {"owner": "bob", "run_id": "run-1", "context": []}, [])
        with self.assertRaises(ValueError):
            values.choose_commitment_action(self.state, {"owner": "alice", "run_id": "run-1", "context": []}, [
                {"action": "repair", "value": "care", "feasible": True, "owner": "bob", "run_id": "run-1"},
            ])

    def test_bounded_retention_duplicates_corrections_and_removal(self):
        first = values.observe_event(self.state, event("same", "care"))
        snapshot = copy.deepcopy(self.state)
        duplicate = values.observe_event(self.state, event("same", "care"))
        self.assertFalse(duplicate["changed"])
        self.assertEqual(self.state, snapshot)
        for index in range(values.MAX_EVIDENCE + 6):
            values.observe_event(self.state, event(f"bound-{index}", "care", status="succeeded" if index % 2 else "failed"))
        self.assertLessEqual(len(self.state["evidence"]), values.MAX_EVIDENCE)
        retained = self.state["evidence"][0]["evidence_id"]
        corrected = event(retained, "care", status="succeeded", context=["repair"])
        values.correct_evidence(self.state, retained, corrected)
        values.remove_evidence(self.state, retained)
        self.assertNotIn(retained, [item["evidence_id"] for item in self.state["evidence"]])
        values.validate(self.state)

    def test_contrary_evidence_revises_commitment(self):
        values.observe_event(self.state, event("positive", "care"))
        self.assertIn("care", self.state["commitments"])
        values.observe_event(self.state, event("negative", "care", status="failed", outcome="harmful"))
        self.assertNotIn("care", self.state["commitments"])
        self.assertLessEqual(self.state["acquired_preferences"]["care"]["score"], 0)


if __name__ == "__main__":
    unittest.main()
