import copy
import json
import unittest

from underworld import communication_f9 as communication


class CommunicationF9Tests(unittest.TestCase):
    def setUp(self):
        self.alice = communication.initial("alice", "run-1")
        self.bob = communication.initial("bob", "run-1")

    def test_empty_initial_lexicon(self):
        self.assertEqual(self.alice["production"], {})
        self.assertEqual(self.alice["comprehension"], {})
        self.assertEqual(self.alice["partner_uncertainty"], {})
        communication.validate(self.alice)

    def test_individual_association_learning(self):
        sent = communication.emit(self.alice, "distress", "bob", "e-emit-1")
        token = sent["token"]
        received = communication.receive(self.bob, "alice", token, "e-delivery-1")
        self.assertIsNone(received["interpretation"]["meaning"])
        self.assertEqual(received["interpretation"]["uncertainty"], 1.0)
        for index in range(3):
            result = communication.learn_from_feedback(
                self.bob, token, "distress", True, f"e-feedback-{index}", "alice")
        self.assertEqual(result["interpretation"]["meaning"], "distress")
        self.assertGreater(result["interpretation"]["confidence"], 0.5)
        self.assertEqual(self.bob["comprehension"]["alice"][token]["successes"], 3)
        self.assertNotIn("distress", self.alice["comprehension"])

    def test_shuffled_tokens_and_unknown_partner_stay_uncertain(self):
        distress = communication.emit(self.alice, "distress", "bob", "e-a")
        relief = communication.emit(self.alice, "relief", "bob", "e-b")
        for token, meaning, index in ((relief["token"], "relief", 1), (distress["token"], "distress", 2)):
            communication.receive(self.bob, "alice", token, f"d-{index}")
            communication.learn_from_feedback(self.bob, token, meaning, True, f"f-{index}", "alice")
        self.assertEqual(communication.interpret(self.bob, "alice", distress["token"])["meaning"], "distress")
        self.assertEqual(communication.interpret(self.bob, "alice", relief["token"])["meaning"], "relief")
        unknown = communication.interpret(self.bob, "carol", distress["token"])
        self.assertIsNone(unknown["meaning"])
        self.assertEqual(unknown["uncertainty"], 1.0)

    def test_feedback_correction_reduces_wrong_association(self):
        message = communication.emit(self.alice, "danger", "bob", "emit-danger")
        token = message["token"]
        communication.receive(self.bob, "alice", token, "deliver-danger")
        for index in range(3):
            communication.learn_from_feedback(self.bob, token, "danger", True, f"right-{index}", "alice")
        before = communication.interpret(self.bob, "alice", token)
        communication.learn_from_feedback(self.bob, token, "danger", False, "correction-1", "alice")
        after = communication.interpret(self.bob, "alice", token)
        self.assertLess(after["confidence"], before["confidence"])
        self.assertEqual(self.bob["comprehension"]["alice"][token]["failures"], 1)

    def test_private_operator_model_and_foreign_state_rejected(self):
        with self.assertRaises(ValueError):
            communication.receive(self.bob, "alice", "bad token", "e1")
        with self.assertRaises(ValueError):
            communication.learn_from_feedback(self.bob, "sig-abcd", "distress", True, "e2", "bob")
        with self.assertRaises(ValueError):
            communication.choose_assistance(
                self.bob,
                {"agent_id": "alice", "run_id": "run-1"},
                [{"meaning": "help", "operator_label": "urgent"}],
            )
        with self.assertRaises(ValueError):
            communication.choose_assistance(
                self.bob,
                {"agent_id": "bob", "run_id": "run-1", "heard": {
                    "speaker": "alice", "token": "sig-abcd", "target_state": {"danger": 1}
                }},
                [{"meaning": "help"}],
            )
        bad = copy.deepcopy(self.bob)
        bad["hidden_state"] = {}
        with self.assertRaises(ValueError):
            communication.validate(bad)

    def test_bounded_evidence_and_duplicate_idempotence(self):
        first = communication.emit(self.alice, "calm", "bob", "same-id")
        snapshot = copy.deepcopy(self.alice)
        self.assertEqual(communication.emit(self.alice, "calm", "bob", "same-id"), first)
        self.assertEqual(self.alice, snapshot)
        for index in range(communication.MAX_EVIDENCE + 8):
            communication.emit(self.alice, "help", "bob", f"bounded-{index}")
        self.assertLessEqual(len(self.alice["evidence"]), communication.MAX_EVIDENCE)
        communication.validate(self.alice)
        with self.assertRaises(ValueError):
            communication.emit(self.alice, "danger", "bob", "same-id")

    def test_json_copy_save_resume_and_assistance_proposal(self):
        sent = communication.emit(self.alice, "help", "bob", "emit-help")
        communication.receive(self.bob, "alice", sent["token"], "deliver-help")
        communication.learn_from_feedback(self.bob, sent["token"], "help", True, "feedback-help", "alice")
        saved = json.loads(json.dumps(self.bob))
        communication.validate(saved)
        proposal = communication.choose_assistance(
            saved,
            {"agent_id": "bob", "run_id": "run-1", "heard": {"speaker": "alice", "token": sent["token"]}},
            [{"meaning": "calm", "action": "wait"}, {"meaning": "help", "action": "offer-assistance"}],
        )
        self.assertEqual(proposal["candidate"]["meaning"], "help")
        self.assertEqual(proposal["execution"], "external")
        self.assertEqual(saved, json.loads(json.dumps(saved)))


if __name__ == "__main__":
    unittest.main()
