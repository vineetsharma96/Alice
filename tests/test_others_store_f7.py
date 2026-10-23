from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

from underworld import others_store_f7 as store
from underworld import storage
from underworld.config import load


def cue(source, name, strength=1.0):
    return {"source_event_id": source, "cue": name, "strength": strength}


def envelope(observer="agent-1", target="agent-2", cues=None, reports=None):
    return {"observer": observer, "target": target,
            "visible_cues": [] if cues is None else cues,
            "social_reports": [] if reports is None else reports}


class OthersStoreF7Tests(unittest.TestCase):
    def test_wire_roundtrip_native_snapshot_is_accepted(self):
        native = json.loads(json.dumps(self.native()))
        result = store.record_observation(self.destination, 'agent-1', native, envelope())
        self.assertIsNotNone(result)

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

    def native(self, observer="agent-1"):
        return storage.observe(self.destination, [observer])[0]

    def test_attach_is_copy_only_and_initializes_all_directional_pairs(self):
        audit = store.inspect(self.destination)
        self.assertEqual(audit["operation_count"], 1)
        self.assertEqual(len(audit["inferences"]), 6)
        self.assertEqual(self.source_bytes, self.source.read_bytes())
        self.assertTrue(store.replay(self.destination)["replay_matches"])
        self.assertEqual(audit["inferences"]["agent-1->agent-2"]["evidence"], [])

    def test_directional_isolation_and_public_only_input(self):
        native = self.native()
        result = store.record_observation(
            self.destination, "agent-1", native,
            envelope(cues=[cue("v-1", "thirst_signal")]))
        audit = store.inspect(self.destination)
        self.assertTrue(result["estimates"]["needs"]["water"]["provenance"] == ["v-1"])
        self.assertEqual(audit["inferences"]["agent-2->agent-1"]["evidence"], [])
        self.assertNotIn("target_private_mood", json.dumps(audit, sort_keys=True))

        private = envelope(cues=[dict(cue("private", "thirst_signal"), target_private_mood=-1)])
        with self.assertRaisesRegex(ValueError, "public fields"):
            store.record_observation(self.destination, "agent-1", native, private)
        operator = dict(envelope(cues=[cue("operator", "calm_posture")]), operator_label="urgent")
        with self.assertRaisesRegex(ValueError, "public fields"):
            store.record_observation(self.destination, "agent-1", native, operator)

    def test_new_public_evidence_corrects_prior_hypothesis(self):
        native = self.native()
        first = store.record_observation(
            self.destination, "agent-1", native,
            envelope(cues=[cue("v-thirst", "thirst_signal")]))
        second = store.record_observation(
            self.destination, "agent-1", native,
            envelope(cues=[cue("v-drink", "drinking_observed")]))
        before = first["estimates"]["needs"]["water"]
        after = second["estimates"]["needs"]["water"]
        self.assertGreater(before["belief"], 0)
        self.assertLess(after["belief"], before["belief"])
        self.assertTrue(second["correction"]["applied"])
        self.assertEqual(after["provenance"], ["v-drink", "v-thirst"])

    def test_idempotence_and_current_stale_foreign_observations(self):
        native = self.native()
        public = envelope(cues=[cue("v-idempotent", "hunger_signal")])
        first = store.record_observation(self.destination, "agent-1", native, public,
                                         operation_id="f7-retry")
        second = store.record_observation(self.destination, "agent-1", native, public,
                                          operation_id="f7-retry")
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["after_hash"], second["after_hash"])
        self.assertEqual(store.inspect(self.destination)["operation_count"], 2)

        storage.advance(self.destination, 1)
        with self.assertRaisesRegex(ValueError, "current native observation"):
            store.record_observation(self.destination, "agent-1", native,
                                     envelope(cues=[cue("v-stale", "calm_posture")]))
        with self.assertRaisesRegex(ValueError, "Foreign"):
            store.record_observation(self.destination, "agent-2", native,
                                     envelope(observer="agent-2", target="agent-1",
                                              cues=[cue("v-foreign", "calm_posture")]))

    def test_backup_resume_replay_in_fresh_process(self):
        store.record_observation(self.destination, "agent-1", self.native(),
                                 envelope(cues=[cue("v-backup", "seeking_shelter")]))
        backup = Path(self.tmp.name) / "backup.sqlite"
        before = self.destination.read_bytes()
        store.save(self.destination, backup)
        self.assertEqual(before, self.destination.read_bytes())
        code = ("from underworld import others_store_f7 as s; import json; "
                "print(json.dumps(s.resume(r'%s'), sort_keys=True))" % backup)
        child = subprocess.run([sys.executable, "-c", code], capture_output=True,
                               text=True, check=True)
        result = json.loads(child.stdout)
        self.assertTrue(result["replay"]["replay_matches"])
        self.assertEqual(result["state_hash"], store.inspect(backup)["state_hash"])

    def test_current_native_projection_uses_public_geometry_only(self):
        native = self.native()
        target = next(item["entity_id"] for item in native["visible_entities"]
                      if item["kind"] == "actor")
        projected = store.public_envelope_from_native(native, target)
        self.assertEqual(projected["observer"], "agent-1")
        self.assertEqual(projected["target"], target)
        self.assertNotIn("target_private_mood", json.dumps(projected))
        self.assertNotIn("body", json.dumps(projected))
        result = store.record_current_observation(self.destination, "agent-1", target)
        self.assertIn("estimates", result)


if __name__ == "__main__":
    unittest.main()
