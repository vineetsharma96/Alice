from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

from underworld import regulation_store_f8 as store
from underworld import storage
from underworld.config import load


def outcome(request_id="r1", strategy="rest", status="completed", cost=3.0):
    action_type = {"rest": "rest", "move_to_safety": "move",
                   "request_help": "request_help", "reconsider": "reconsider",
                   "switch_plan": "switch_plan"}[strategy]
    return {"request_id": request_id, "status": status, "action_type": action_type,
            "strategy": strategy, "result": {}, "estimated_cost_s": cost}


def candidate(strategy="rest"):
    actions = {
        "rest": ("rest", {"seconds": 2.0}),
        "move_to_safety": ("move", {"destination": "shelter"}),
        "request_help": ("request_help", {"reason": "safety"}),
        "reconsider": ("reconsider", {"reason": "review"}),
        "switch_plan": ("switch_plan", {"plan": "fallback"}),
    }
    action_type, parameters = actions[strategy]
    return {"strategy": strategy, "action_type": action_type,
            "parameters": parameters, "requested_duration": 2.0,
            "estimated_cost_s": 1.0}


class RegulationStoreF8Tests(unittest.TestCase):
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

    def native(self, owner="agent-1"):
        return storage.observe(self.destination, [owner])[0]

    def before_with_stress(self, owner="agent-1", stress=0.7):
        before = copy.deepcopy(self.native(owner))
        before.setdefault("own_state", {})["affect"] = {"stress": stress, "fear": 0.0}
        return before

    def test_attach_is_copy_only_and_initializes_all_owners(self):
        audit = store.inspect(self.destination)
        self.assertEqual(audit["operation_count"], 1)
        self.assertEqual(set(audit["regulation"]), {"agent-1", "agent-2", "agent-3"})
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertTrue(store.replay(self.destination)["replay_matches"])

    def test_current_outcome_updates_only_owner_and_is_publicly_bounded(self):
        result = store.record_current_outcome(
            self.destination, "agent-1", self.before_with_stress(), outcome())
        self.assertEqual(result["owner"], "agent-1")
        self.assertEqual(result["evidence"]["request_id"], "r1")
        audit = store.inspect(self.destination)
        self.assertEqual(audit["regulation"]["agent-2"]["evidence"], [])
        self.assertTrue(store.replay(self.destination)["replay_matches"])

    def test_choose_uses_current_native_observation_and_rejects_stale_after(self):
        selected = store.choose(self.destination, "agent-1", [candidate("rest")])
        self.assertEqual(selected["strategy"], "rest")
        native = self.native()
        storage.advance(self.destination, 1)
        with self.assertRaisesRegex(ValueError, "current native observation"):
            store.record_outcome(self.destination, "agent-1", self.before_with_stress(),
                                 outcome("stale"), after=native)

    def test_idempotence_private_rejection_and_backup_resume(self):
        before = self.before_with_stress()
        first = store.record_current_outcome(self.destination, "agent-1", before,
                                             outcome("retry"), operation_id="f8-retry")
        second = store.record_current_outcome(self.destination, "agent-1", before,
                                              outcome("retry"), operation_id="f8-retry")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["after_hash"], second["after_hash"])
        private = outcome("private")
        private["target_private_mood"] = -1
        with self.assertRaisesRegex(ValueError, "private"):
            store.record_current_outcome(self.destination, "agent-1", before, private)

        backup = Path(self.tmp.name) / "backup.sqlite"
        original = self.destination.read_bytes()
        store.save(self.destination, backup)
        self.assertEqual(original, self.destination.read_bytes())
        code = ("from underworld import regulation_store_f8 as s; import json; "
                "print(json.dumps(s.resume(r'%s'), sort_keys=True))" % backup)
        child = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, check=True)
        result = json.loads(child.stdout)
        self.assertTrue(result["replay"]["replay_matches"])


if __name__ == "__main__":
    unittest.main()
