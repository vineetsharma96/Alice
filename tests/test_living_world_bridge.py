from pathlib import Path
import tempfile
import unittest

from underworld import life_store
from underworld import living_world_bridge as bridge
from underworld import weather_policy as policy
from underworld import weather_tools as tools


class LivingWorldBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.sqlite"
        self.path = self.root / "living.sqlite"
        life_store.initialize_source(self.source, seed=61, population=2)

    def attach(self):
        return bridge.attach(self.source, self.path, biological_step_s=1.0)

    def test_attach_binds_all_foundations_without_mutating_source(self):
        original = self.source.read_bytes()
        result = self.attach()
        self.assertEqual(original, self.source.read_bytes())
        self.assertEqual(result["native_tick"], 0)
        self.assertEqual(
            set(result["sidecars"]), {"g01", "g47", "l02", "l59", "m03", "m48"}
        )
        self.assertEqual(result["actors"], ["agent-1", "agent-2"])
        state = bridge.state(self.path)
        self.assertEqual(set(state["l02"]["individuals"]), set(result["actors"]))
        self.assertEqual(set(state["l59"]["individuals"]), set(result["actors"]))
        self.assertEqual(state["m48"]["disease"]["status"], "disabled")

    def test_native_ticks_advance_every_sidecar_and_retry_is_idempotent(self):
        self.attach()
        before = bridge.state(self.path)
        result = bridge.commit(self.path, {"kind": "step", "ticks": 4}, "step-1")
        self.assertEqual(result["sidecars"]["native_tick_after"], 4)
        after = bridge.state(self.path)
        self.assertEqual(bridge.inspect(self.path)["native_tick"], 4)
        self.assertEqual(after["g01"]["revision"], before["g01"]["revision"] + 1)
        self.assertEqual(after["g47"]["revision"], before["g47"]["revision"] + 1)
        self.assertEqual(after["m03"]["revision"], before["m03"]["revision"] + 1)
        self.assertEqual(after["m48"]["revision"], before["m48"]["revision"] + 1)
        self.assertEqual(after["l02"]["clock_step"], 1)
        self.assertEqual(after["l59"]["clock_step"], 1)
        retry = bridge.commit(self.path, {"kind": "step", "ticks": 4}, "step-1")
        self.assertTrue(retry["idempotent"])
        self.assertEqual(bridge.inspect(self.path)["native_tick"], 4)

    def test_native_public_receipt_updates_l02_relationship_state(self):
        world = tools.JournalWorld(self.source)
        tools.walk(world, [3.1, 3], agent="agent-2")
        self.assertEqual(
            tools.execute(world, "gather", "resource-1", {"mass_kg": 0.2})["status"],
            "completed",
        )
        self.attach()
        choice = policy.option(
            "give", {"material": "food", "mass_kg": 0.15},
            "agent-2", 1, "assigned_transfer",
        )
        result = bridge.commit(
            self.path,
            {"kind": "life-act", "agent": "agent-1", "choice": choice},
            "give-1",
        )
        self.assertEqual(result["native_effect"]["status"], "completed")
        state = bridge.state(self.path)
        self.assertIn("agent-1->agent-2", state["l02"]["relationships"])
        self.assertEqual(state["l02"]["relationships"]["agent-1->agent-2"]["trust"], 0.1)

    def test_save_resume_and_fresh_replay_validate_native_and_sidecars(self):
        self.attach()
        bridge.run(self.path, 4)
        backup = self.root / "backup.sqlite"
        bridge.save(self.path, backup)
        result = bridge.replay(backup)
        self.assertTrue(result["replay_matches"])
        self.assertTrue(result["native"]["replay_matches"])
        self.assertTrue(result["life"]["verified"])
        self.assertEqual(bridge.inspect(self.path)["state_hash"], bridge.inspect(backup)["state_hash"])


if __name__ == "__main__":
    unittest.main()
