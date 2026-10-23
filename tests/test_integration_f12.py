import json
from contextlib import closing
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from typing import Any

from underworld import integration_f12 as integration
from underworld import storage
from underworld.config import load


ROOT = Path(__file__).resolve().parents[1]


def f8_candidate():
    return {"strategy": "rest", "action_type": "rest",
            "parameters": {"seconds": 1.0}, "requested_duration": 1.0,
            "estimated_cost_s": 1.0}


class IntegrationF12Tests(unittest.TestCase):
    def test_real_action_interval_is_not_the_whole_telemetry_segment(self):
        # The baseline fixture has no bodies; use the native bodies profile.
        source=self.root/'bodies.sqlite';path=self.root/'bodies-f12.sqlite'
        config=load(ROOT/'config/living-world.toml');config['world']['population']=2
        storage.create(source,config,scripted=False);integration.attach(source,path)
        self.destination=path
        observation=storage.observe(self.destination,['agent-1'])[0]
        request={'schema_version':1,'run_id':observation['run_id'],'request_id':'actual-rest',
            'agent_id':'agent-1','observation_version':observation['tick'],'action_type':'rest',
            'target_ids':[],'parameters':{},'requested_duration':1.0}
        storage.advance(self.destination,20,decisions=[(int(observation['tick']),request)])
        r=integration.record_native_outcome(self.destination,'agent-1','actual-rest')
        self.assertEqual(r['evidence_provenance'],'native_journal_verified')
        self.assertEqual(r['evidence']['elapsed_s'],1.0)
        self.assertTrue(integration.replay(self.destination)['replay_matches'])
        before=integration.inspect(self.destination)
        for owner,rid in [('agent-1','made-up'),('agent-2','actual-rest')]:
            with self.assertRaises(ValueError):integration.record_native_outcome(self.destination,owner,rid)
        self.assertEqual(before,integration.inspect(self.destination))
        import sqlite3
        with closing(sqlite3.connect(self.destination)) as db:
            db.execute("UPDATE decisions SET result='{}' WHERE json_extract(request,'$.request_id')='actual-rest'")
            db.commit()
        with self.assertRaisesRegex(ValueError,'Native decision'):
            integration.replay(self.destination)

    def test_operation_identity_includes_operation_kind(self):
        event = self.event('kind-conflict', 'represented_standard', provenance='seeded')
        integration.observe_social(self.destination, 'agent-1', event, operation_id='same-kind-id')
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            integration.revise_identity(self.destination, 'agent-1', event, operation_id='same-kind-id')

    def test_attach_preserves_existing_f8_learning(self):
        from underworld import regulation_store_f8
        f8 = self.root / 'f8.sqlite'
        regulation_store_f8.attach(self.source, f8)
        observation = storage.observe(f8, ['agent-1'])[0]
        regulation_store_f8.record_outcome(f8, 'agent-1', observation,
            {'request_id':'guided-existing', 'status':'completed', 'action_type':'rest',
             'strategy':'rest', 'result':{}, 'estimated_cost_s':1})
        inherited = self.root / 'inherited.sqlite'
        result = integration.attach(f8, inherited)
        self.assertEqual(result['overlay_summaries']['agent-1']['f8']['revision'], 1)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.sqlite"
        self.destination = self.root / "f12.sqlite"
        config = load(ROOT / "config/baseline.toml")
        config["world"].update(population=2, width_m=8.0, height_m=8.0)
        storage.create(self.source, config, scripted=False)
        self.source_bytes = self.source.read_bytes()
        self.attached = integration.attach(self.source, self.destination,
                                           declared_values=["care"])
        self.run_id = self.attached["run_id"]

    def event(self, evidence_id, predicate, *, kind="own_observation",
              subject="case-1", other=None, value: Any = True, provenance="learned",
              owner="agent-1", run_id=None):
        return {"evidence_id": evidence_id, "kind": kind, "owner": owner,
                "run_id": self.run_id if run_id is None else run_id, "provenance": provenance,
                "predicate": predicate, "subject": subject, "value": value,
                "other": other}

    def value_event(self, evidence_id, value="care", status="succeeded"):
        return {"evidence_id": evidence_id, "kind": "native_outcome",
                "owner": "agent-1", "run_id": self.run_id, "provenance": "native",
                "status": status, "value": value, "outcome": "completed",
                "context": ["shelter"], "source": "native:" + evidence_id}

    def test_attach_copy_initializes_all_actors_and_overlays(self):
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertEqual(self.attached["actors"], ["agent-1", "agent-2"])
        self.assertEqual(self.attached["native_tick"], 0)
        self.assertEqual(set(self.attached["overlay_summaries"]), {"agent-1", "agent-2"})
        for summary in self.attached["overlay_summaries"].values():
            self.assertEqual(summary["f8"]["evidence_count"], 0)
            self.assertEqual(summary["f9"]["evidence_count"], 0)
            self.assertEqual(summary["f10"]["evidence_count"], 0)
            self.assertEqual(summary["f11"]["evidence_count"], 0)
        self.assertEqual(self.attached["operation_count"], 1)

    def test_current_observation_and_strict_foreign_stale_rejection(self):
        observation = integration.observe_current(self.destination, "agent-1")
        self.assertEqual(observation["observation"]["agent_id"], "agent-1")
        self.assertEqual(observation["observation"]["run_id"], self.run_id)
        with self.assertRaises(ValueError):
            integration.observe_current(self.destination, "agent-1", {
                **observation["observation"], "agent_id": "agent-2"},
                {"request_id": "r", "status": "completed", "action_type": "rest",
                 "strategy": "rest", "result": {}, "estimated_cost_s": 0.0})
        with self.assertRaises(ValueError):
            integration.observe_social(self.destination, "agent-1",
                                       self.event("foreign", "received_help",
                                                   owner="agent-2"))

    def test_f8_updates_from_actual_current_native_snapshot(self):
        before = integration.observe_current(self.destination, "agent-1")["observation"]
        outcome = {"request_id": "f8-r1", "status": "completed", "action_type": "rest",
                   "strategy": "rest", "result": {}, "estimated_cost_s": 2.5}
        result = integration.observe_current(self.destination, "agent-1", before, outcome)
        self.assertEqual(result["evidence"]["request_id"], "f8-r1")
        self.assertEqual(result["evidence"]["cost_s"], 2.5)
        self.assertEqual(integration.inspect(self.destination)["overlay_summaries"]["agent-1"]["f8"]["evidence_count"], 1)

    def test_f9_send_receive_feedback_persist(self):
        sent = integration.send_signal(self.destination, "agent-1", "help", "agent-2", "emit-1")
        token = sent["token"]
        received = integration.receive_signal(self.destination, "agent-2", "agent-1", token, "deliver-1")
        self.assertIsNone(received["interpretation"]["meaning"])
        feedback = integration.feedback_signal(self.destination, "agent-2", token, "help", True,
                                               "feedback-1", "agent-1")
        self.assertTrue(feedback["changed"])
        summary = integration.inspect(self.destination)["overlay_summaries"]["agent-2"]["f9"]
        self.assertEqual(summary["evidence_count"], 2)
        self.assertEqual(summary["partner_count"], 1)

    def test_f10_prerequisite_and_f11_value_summary(self):
        integration.observe_social(self.destination, "agent-1",
                                   self.event("help-1", "received_help", kind="relationship",
                                               other="agent-2", value="water"))
        pending = integration.observe_social(self.destination, "agent-1",
                                             self.event("benefit-1", "recognized_benefit",
                                                         value="water"))
        self.assertIn("gratitude", pending["state"]["states"])
        acquired = integration.revise_identity(self.destination, "agent-1",
                                                self.value_event("value-1"))
        self.assertTrue(acquired["changed"])
        revised = integration.revise_identity(
            self.destination, "agent-1",
            {"summary": {"text": "protect nearby life", "claims": ["care"],
                          "contexts": ["shelter"]}, "evidence_id": "value-1"})
        self.assertTrue(revised["changed"])

    def test_choose_is_proposal_only_and_does_not_advance_native(self):
        before = integration.inspect(self.destination)
        choice = integration.choose(self.destination, "agent-1", {
            "f8": [f8_candidate()],
            "f9": [{"meaning": "help", "action": "offer-assistance"}],
            "f10": [{"action": "repair"}],
            "f11": [{"action": "care", "value": "care", "feasible": True}],
        })
        after = integration.inspect(self.destination)
        self.assertTrue(choice["proposal_only"])
        self.assertEqual(choice["choices"]["f8"]["strategy"], "rest")
        self.assertEqual(before["native_tick"], after["native_tick"])
        self.assertEqual(before["state_hash"], after["state_hash"])
        self.assertEqual(before["operation_count"], after["operation_count"])

    def test_idempotent_retry_and_private_foreign_rejection(self):
        first = integration.send_signal(self.destination, "agent-1", "calm", "agent-2", "same",
                                         operation_id="retry-1")
        second = integration.send_signal(self.destination, "agent-1", "calm", "agent-2", "same",
                                         operation_id="retry-1")
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["after_hash"], second["after_hash"])
        with self.assertRaises(ValueError):
            integration.send_signal(self.destination, "agent-1", "help", "agent-2", "same",
                                    operation_id="retry-1")
        with self.assertRaises(ValueError):
            integration.send_signal(self.destination, "agent-1", "help", "agent-9", "bad")
        with self.assertRaises(ValueError):
            integration.observe_social(self.destination, "agent-1", {
                **self.event("private", "received_help"), "private_state": {"x": 1}})

    def test_save_resume_replay_fresh_process_and_final_smoke(self):
        before_native = storage.inspect(self.destination)
        before_bytes = self.source.read_bytes()
        f8_before = integration.observe_current(self.destination, "agent-1")["observation"]
        integration.observe_current(self.destination, "agent-1", f8_before, {
            "request_id": "smoke-f8", "status": "completed", "action_type": "rest",
            "strategy": "rest", "result": {}, "estimated_cost_s": 1.0})
        sent = integration.send_signal(self.destination, "agent-1", "distress", "agent-2", "smoke-send")
        integration.receive_signal(self.destination, "agent-2", "agent-1", sent["token"], "smoke-receive")
        integration.feedback_signal(self.destination, "agent-2", sent["token"], "distress", True,
                                    "smoke-feedback", "agent-1")
        integration.observe_social(self.destination, "agent-1",
                                   self.event("smoke-help", "received_help", kind="relationship",
                                               other="agent-2", value="water"))
        integration.observe_social(self.destination, "agent-1",
                                   self.event("smoke-benefit", "recognized_benefit", value="water"))
        integration.revise_identity(self.destination, "agent-1", self.value_event("smoke-value"))
        backup = self.root / "backup.sqlite"
        integration.save(self.destination, backup)
        resumed = integration.resume(backup)
        self.assertTrue(resumed["replay"]["replay_matches"])
        code = "from underworld import integration_f12; import sys; print(integration_f12.replay(sys.argv[1])['replay_matches'])"
        fresh = subprocess.run([sys.executable, "-c", code, str(backup)], cwd=ROOT,
                               capture_output=True, text=True, check=True)
        self.assertEqual(fresh.stdout.strip(), "True")
        self.assertEqual(int(before_native["tick"]), integration.inspect(self.destination)["native_tick"])
        self.assertEqual(before_bytes, self.source.read_bytes())

    def test_manifest_reports_bounded_unverified_gates(self):
        report = integration.manifest(self.destination, wall_time_s=0.25)
        self.assertEqual(report["simulated_tick"], 0)
        self.assertEqual(report["wall_time_s"], 0.25)
        self.assertIn("autonomous scheduler integration", report["unverified_gates"])


if __name__ == "__main__":
    unittest.main()
