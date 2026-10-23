import copy
import json
import unittest
from typing import Any

from underworld import social_emotions_f10 as emotions


def event(evidence_id, predicate, *, kind="own_observation", subject="case-1",
          other=None, value: Any = True, provenance="learned", owner="alice", run_id="run-1"):
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "owner": owner,
        "run_id": run_id,
        "provenance": provenance,
        "predicate": predicate,
        "subject": subject,
        "value": value,
        "other": other,
    }


class SocialEmotionsF10Tests(unittest.TestCase):
    def setUp(self):
        self.state = emotions.initial("alice", "run-1")

    def add(self, evidence_id, predicate, **kwargs):
        return emotions.observe_event(self.state, event(evidence_id, predicate, **kwargs))

    def test_unavailable_prerequisites_are_deferred(self):
        self.assertFalse(emotions.available(self.state, "gratitude"))
        result = self.add("h1", "received_help", kind="relationship", other="bob", value="water")
        self.assertFalse(emotions.available(self.state, "gratitude"))
        self.assertIn("recognized_benefit", result["deferred"]["gratitude"])
        self.assertNotIn("gratitude", self.state["states"])

    def test_each_prerequisite_gate_is_required(self):
        gates = {
            "gratitude": ("received_help", "recognized_benefit"),
            "pride": ("completed_achievement", "represented_standard"),
            "guilt": ("perceived_responsibility", "violated_expectation", "feasible_repair"),
            "embarrassment": ("public_exposure", "represented_norm"),
            "envy": ("observed_other_benefit", "self_relevant_comparison"),
            "grief": ("established_attachment", "loss_observed"),
        }
        for emotion, predicates in gates.items():
            fresh = emotions.initial("alice", "run-1")
            for index, predicate in enumerate(predicates[:-1]):
                kwargs = {"subject": emotion + "-case"}
                if emotion in {"envy", "grief"} and predicate in {"observed_other_benefit", "established_attachment"}:
                    kwargs.update(kind="relationship", other="bob")
                if emotion == "envy" and predicate == "self_relevant_comparison":
                    kwargs.update(other="bob")
                emotions.observe_event(fresh, event(f"{emotion}-{index}", predicate, **kwargs))
            self.assertFalse(emotions.available(fresh, emotion), emotion)

    def test_all_gates_become_available_only_with_linked_evidence(self):
        cases = {
            "gratitude": [
                event("g1", "received_help", kind="relationship", other="bob", value="water"),
                event("g2", "recognized_benefit", value="water"),
            ],
            "pride": [event("p1", "completed_achievement"), event("p2", "represented_standard")],
            "guilt": [event("u1", "perceived_responsibility"), event("u2", "violated_expectation"), event("u3", "feasible_repair")],
            "embarrassment": [event("b1", "public_exposure"), event("b2", "represented_norm")],
            "envy": [
                event("e1", "observed_other_benefit", kind="relationship", other="bob"),
                event("e2", "self_relevant_comparison", kind="relationship", other="bob"),
            ],
            "grief": [
                event("r1", "established_attachment", kind="relationship", other="bob"),
                event("r2", "loss_observed", kind="relationship", other="bob", subject="loss-1"),
            ],
        }
        for emotion, events in cases.items():
            fresh = emotions.initial("alice", "run-1")
            for item in events:
                emotions.observe_event(fresh, item)
            self.assertTrue(emotions.available(fresh, emotion), emotion)
            self.assertTrue(fresh["states"][emotion]["evidence"])
            emotions.validate(fresh)

    def test_directional_relationship_isolation_and_foreign_identity_rejection(self):
        alice = emotions.initial("alice", "run-1")
        bob = emotions.initial("bob", "run-1")
        emotions.observe_event(alice, event("a1", "established_attachment", kind="relationship", other="carol"))
        self.assertEqual(bob["evidence"], [])
        with self.assertRaises(ValueError):
            emotions.observe_event(alice, event("x1", "loss_observed", kind="relationship", other="carol", owner="bob"))
        with self.assertRaises(ValueError):
            emotions.observe_event(alice, event("x2", "loss_observed", kind="relationship", other="alice"))

    def test_guilt_drives_only_repair_candidate(self):
        for evidence_id, predicate in (("u1", "perceived_responsibility"),
                                       ("u2", "violated_expectation"),
                                       ("u3", "feasible_repair")):
            self.add(evidence_id, predicate, subject="repair-case")
        proposal = emotions.influence(self.state, [
            {"action": "gratitude", "target": "bob"},
            {"action": "repair", "target": "bob"},
        ])
        assert proposal is not None
        self.assertEqual(proposal["action"], "repair")
        self.assertEqual(proposal["emotion"], "guilt")
        self.assertEqual(proposal["execution"], "external")

    def test_grief_requires_attachment_and_loss_and_can_seek_connection(self):
        self.add("a1", "established_attachment", kind="relationship", other="bob", subject="bond")
        self.assertFalse(emotions.available(self.state, "grief"))
        self.add("l1", "loss_observed", kind="relationship", other="bob", subject="loss")
        self.assertTrue(emotions.available(self.state, "grief"))
        proposal = emotions.influence(self.state, [{"action": "seek_connection", "target": "bob"}])
        assert proposal is not None
        self.assertEqual(proposal["action"], "seek_connection")
        self.assertEqual(proposal["target"], "bob")

    def test_bounded_evidence_idempotence_and_correction_removal(self):
        first = self.add("same", "received_help", kind="relationship", other="bob")
        snapshot = copy.deepcopy(self.state)
        duplicate = emotions.observe_event(self.state, event("same", "received_help", kind="relationship", other="bob"))
        self.assertFalse(duplicate["changed"])
        self.assertEqual(self.state, snapshot)
        with self.assertRaises(ValueError):
            emotions.observe_event(self.state, event("same", "recognized_benefit"))
        for index in range(emotions.MAX_EVIDENCE + 5):
            self.add(f"bound-{index}", "recognized_benefit", subject=f"case-{index}")
        self.assertLessEqual(len(self.state["evidence"]), emotions.MAX_EVIDENCE)
        emotions.correct_evidence(self.state, "bound-30", event("bound-30", "recognized_benefit", subject="corrected"))
        emotions.remove_evidence(self.state, "bound-31")
        emotions.validate(self.state)
        self.assertNotIn("bound-31", [item["evidence_id"] for item in self.state["evidence"]])

    def test_json_copy_save_resume_and_actual_candidate_influence(self):
        for evidence_id, predicate in (("u1", "perceived_responsibility"),
                                       ("u2", "violated_expectation"),
                                       ("u3", "feasible_repair")):
            self.add(evidence_id, predicate, subject="resume-case", provenance="taught")
        saved = json.loads(json.dumps(self.state))
        emotions.validate(saved)
        proposal = emotions.influence(saved, [{"action": "repair"}, {"action": "seek_connection"}])
        assert proposal is not None
        self.assertEqual(proposal["action"], "repair")
        self.assertEqual(saved, json.loads(json.dumps(saved)))

    def test_private_model_labels_unsupported_claims_and_bad_provenance_rejected(self):
        bad = event("bad", "received_help")
        bad["operator_label"] = "gratitude"
        with self.assertRaises(ValueError):
            emotions.observe_event(self.state, bad)
        bad = event("bad2", "received_help", provenance="invented")
        with self.assertRaises(ValueError):
            emotions.observe_event(self.state, bad)
        bad = event("bad3", "received_help")
        bad["emotion"] = "grief"
        with self.assertRaises(ValueError):
            emotions.observe_event(self.state, bad)


if __name__ == "__main__":
    unittest.main()
