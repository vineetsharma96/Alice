from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

from underworld import relationships_f6 as relationships
from underworld import relationship_store_f6 as store
from underworld import storage
from underworld.config import load


def event(observer, other, kind, seq, tick):
    return {"observer": observer, "other": other, "kind": kind,
            "source_event_seq": str(seq), "tick": tick}


class RelationshipStoreF6Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config = copy.deepcopy(load(Path(__file__).parents[1] / "config/culture.toml"))
        config["world"]["population"] = 3
        self.source = Path(self.tmp.name) / "source.sqlite"
        self.destination = Path(self.tmp.name) / "destination.sqlite"
        storage.create(self.source, config, scripted=False)
        self.source_bytes = self.source.read_bytes()
        store.attach(self.source, self.destination)

    def test_attach_initializes_directional_pairs_without_touching_source(self):
        audit = store.inspect(self.destination)
        self.assertEqual(audit["operation_count"], 1)
        self.assertEqual(len(audit["relationships"]), 6)
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertTrue(storage.replay(self.destination)["replay_matches"])
        for key, state in audit["relationships"].items():
            self.assertEqual(state["observations"], 0, key)
            self.assertNotEqual(state["owner"], state["other"])

    def test_directional_history_changes_helper_ranking_and_reverse_edge_stays_empty(self):
        store.record_events(self.destination, [event("agent-1", "agent-2", "task_failed", 1, 1),
                                               event("agent-1", "agent-3", "task_completed", 2, 2)])
        audit = store.inspect(self.destination)
        self.assertLess(audit["relationships"]["agent-1->agent-2"]["trust"], 0)
        self.assertGreater(audit["relationships"]["agent-1->agent-3"]["trust"], 0)
        self.assertEqual(audit["relationships"]["agent-2->agent-1"]["observations"], 0)
        trusted = relationships.choose_helper(
            {"agent-2": audit["relationships"]["agent-1->agent-2"],
             "agent-3": audit["relationships"]["agent-1->agent-3"]},
            ["agent-2", "agent-3"])
        self.assertIsNotNone(trusted)
        assert trusted is not None
        self.assertEqual(trusted["other"], "agent-3")

        store.record_events(self.destination, [event("agent-1", "agent-2", "task_completed", 3, 3),
                                               event("agent-1", "agent-2", "task_completed", 4, 4)])
        repaired = store.inspect(self.destination)["relationships"]["agent-1->agent-2"]
        self.assertGreater(repaired["trust"], -0.1)

    def test_strict_observation_rejects_private_fields_and_retry_is_idempotent(self):
        observation = storage.observe(self.destination, ["agent-1"])[0]
        observation["social_reports"] = [{"source_event_seq": "17", "tick": "4",
                                           "other": "agent-2", "kind": "task_completed",
                                           "target_private_mood": -1}]
        with self.assertRaisesRegex(ValueError, "native witnessed fields"):
            store._native_social_event("agent-1", observation["social_reports"][0])
        with self.assertRaisesRegex(ValueError, "current native observation"):
            store.record_observation(self.destination, "agent-1", observation)
        accepted = event("agent-1", "agent-2", "resource_given", 21, 8)
        first = store.record_events(self.destination, [accepted], operation_id="op-21")
        second = store.record_events(self.destination, [accepted], operation_id="op-21")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["after_hash"], second["after_hash"])
        self.assertEqual(store.inspect(self.destination)["operation_count"], 2)

    def test_completed_task_response_receipt_uses_public_offer_to_find_directional_peer(self):
        observation = storage.observe(self.destination, ["agent-2"])[0]
        observation["task_offers"] = [{"id": "agreement-1", "proposer": "agent-1",
                                       "partner": "agent-2", "status": "offered"}]
        observation["recent_action_results"] = [{"request_id": "response-1", "status": "completed",
                                                   "completed_tick": observation["tick"], "event_refs": ["91"]}]

        class ReceiptDB:
            def execute(self, query, params=()):
                self.query, self.params = query, params
                return [(json.dumps({
                    "request_id": "response-1", "agent_id": "agent-2",
                    "action_type": "respond_task", "target_ids": [],
                    "parameters": {"agreement_id": "agreement-1", "accept": True}}),)]

        events = store._receipt_events(ReceiptDB(), "agent-2", observation,
                                       ["agent-1", "agent-2", "agent-3"])
        self.assertEqual(events[0]["other"], "agent-1")
        self.assertEqual(events[0]["kind"], "task_accepted")

    def test_empty_visible_candidates_return_no_choice_and_backup_replays_in_fresh_process(self):
        store.record_events(self.destination, [event("agent-1", "agent-2", "task_completed", 31, 4)])
        self.assertIsNone(store.choose_helper(self.destination, "agent-1", ["agent-99"]))
        backup = Path(self.tmp.name) / "backup.sqlite"
        before = self.destination.read_bytes()
        store.save(self.destination, backup)
        self.assertEqual(before, self.destination.read_bytes())
        code = "from underworld import relationship_store_f6 as s; import json; print(json.dumps(s.resume(r'%s'), sort_keys=True))" % backup
        child = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        result = json.loads(child.stdout)
        self.assertTrue(result["replay"]["replay_matches"])
        self.assertEqual(result["state_hash"], store.inspect(backup)["state_hash"])


if __name__ == "__main__":
    unittest.main()
