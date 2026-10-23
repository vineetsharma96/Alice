from contextlib import closing
import inspect
from pathlib import Path
import tempfile
import unittest

from underworld import developmental as dev, storage, symbols, teaching, wayfinding as wf


class WayfindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'world.sqlite'
        wf.initialize(self.path, 43)
        wf.walk(self.path, 'agent-2', [3, 3])

    def speech(self):
        wf.remember_site(self.path, 'agent-2')
        token = wf.coin_site(self.path, 'agent-1')
        return dev.execute(self.path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)

    def relief(self):
        g = dev.execute(self.path, 'agent-2', 'gather', ['resource-2'], {'mass_kg': .05}, update_memory=False)
        c = dev.execute(self.path, 'agent-2', 'drink', parameters={'mass_kg': .05}, update_memory=False)
        return g['request']['request_id'], c['request']['request_id']

    def test_new_cohort_has_empty_private_location_and_need_memories(self):
        audit = wf.audit(self.path)
        self.assertEqual(len(audit['people']), 4)
        for state in audit['people'].values():
            self.assertEqual(state['h4']['sites'], {})
            self.assertEqual(state['h4']['outcomes'], {})
        with self.assertRaisesRegex(ValueError, 'private wayfinding access'):
            wf.private(self.path, 'agent-1', 'agent-2')
        with self.assertRaises(Exception):
            wf.initialize(self.path, 43)

    def test_location_learning_uses_native_covisit_and_is_idempotent(self):
        speech = self.speech()
        proof = wf.learn_site(self.path, 'agent-2', 'agent-1')
        state = wf.private(self.path, 'agent-2', 'agent-2')
        self.assertEqual(wf.learn_site(self.path, 'agent-2', 'agent-1'), proof)
        self.assertEqual(wf.private(self.path, 'agent-2', 'agent-2'), state)
        self.assertIn(proof['message']['source_event_seq'], speech['native_events'])
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_location_update_rollback_and_postcommit_recovery(self):
        self.speech()
        def fail(stage):
            raise RuntimeError(stage)
        with self.assertRaisesRegex(RuntimeError, 'before_commit'):
            wf.learn_site(self.path, 'agent-2', 'agent-1', fault=fail)
        self.assertEqual(wf.private(self.path, 'agent-2', 'agent-2')['location_comprehension'], {})
        def after(stage):
            if stage == 'after_commit':
                raise RuntimeError(stage)
        with self.assertRaisesRegex(RuntimeError, 'after_commit'):
            wf.learn_site(self.path, 'agent-2', 'agent-1', fault=after)
        wf.learn_site(self.path, 'agent-2', 'agent-1')
        entries = wf.private(self.path, 'agent-2', 'agent-2')['location_comprehension']
        self.assertEqual(sum(e['n'] for m in entries.values() for e in m.values()), 1)

    def test_old_speech_cannot_ground_current_position(self):
        self.speech()
        dev.execute(self.path, 'agent-2', 'rest', duration=4, update_memory=False)
        with self.assertRaisesRegex(ValueError, 'fresh co-located'):
            wf.learn_site(self.path, 'agent-2', 'agent-1')

    def test_resource_token_does_not_supply_location(self):
        token = symbols.coin(self.path, 'agent-1', 'resource-2')
        dev.execute(self.path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)
        report = wf.receive(self.path, 'agent-2', 'agent-1')
        self.assertIsNone(report['location'])
        self.assertFalse(report['verified'])
        self.assertEqual(wf.private(self.path, 'agent-2', 'agent-2')['location_comprehension'], {})

    def test_report_remains_unverified_and_repeated_receive_does_not_update(self):
        self.speech()
        wf.learn_site(self.path, 'agent-2', 'agent-1')
        result = wf.receive(self.path, 'agent-2', 'agent-1')
        before = wf.audit(self.path)
        self.assertFalse(result['verified'])
        self.assertIsNotNone(result['location'])
        self.assertEqual(wf.receive(self.path, 'agent-2', 'agent-1'), result)
        self.assertEqual(wf.audit(self.path), before)

    def test_native_relief_update_is_once_and_conflicting_identity_refused(self):
        g, c = self.relief()
        result = wf.learn_relief(self.path, 'agent-2', g, c)
        before = wf.audit(self.path)
        self.assertEqual(wf.learn_relief(self.path, 'agent-2', g, c), result)
        self.assertEqual(wf.audit(self.path), before)
        with self.assertRaisesRegex(ValueError, 'conflicting outcome'):
            wf.learn_relief(self.path, 'agent-2', 'wrong-gather', c)

    def test_relief_crash_recovery_preserves_native_consumption(self):
        g, c = self.relief()
        head = storage.inspect(self.path)['state_hash']
        def fail(stage):
            if stage == 'after_commit':
                raise RuntimeError('after_commit')
        with self.assertRaises(RuntimeError):
            wf.learn_relief(self.path, 'agent-2', g, c, fail)
        wf.learn_relief(self.path, 'agent-2', g, c)
        self.assertEqual(storage.inspect(self.path)['state_hash'], head)
        self.assertEqual(sum(e['n'] for e in wf.private(self.path, 'agent-2', 'agent-2')['outcomes'].values()), 1)

    def test_need_choice_requires_own_learned_predictions(self):
        g, c = self.relief()
        wf.learn_relief(self.path, 'agent-2', g, c)
        for _ in range(2):
            dev.execute(self.path, 'agent-2', 'rest', duration=60, update_memory=False)
        self.assertEqual(wf.choose_goal(self.path, 'agent-2')['goal']['action'], 'drink')
        self.assertIsNone(wf.choose_goal(self.path, 'agent-2', frozen=True)['goal'])
        self.assertNotIn('target', inspect.signature(wf.choose_goal).parameters)

    def test_need_step_consumes_carried_supplies_without_gathering_twice(self):
        g, c = self.relief()
        wf.learn_relief(self.path, 'agent-2', g, c)
        dev.execute(self.path, 'agent-2', 'gather', ['resource-2'], {'mass_kg': .05}, update_memory=False)
        for _ in range(2):
            dev.execute(self.path, 'agent-2', 'rest', duration=60, update_memory=False)
        result = wf.policy_step(self.path, 'agent-2')
        self.assertTrue(result['execution']['goal_completed'])
        self.assertTrue(result['execution']['used_carried'])
        self.assertEqual([a['request']['action_type'] for a in result['execution']['actions']], ['drink'])
        self.assertEqual(wf.private(self.path, 'agent-2', 'agent-2')['policy_decisions'], 1)

    def test_missing_need_proof_stops_selection_before_execution(self):
        g, c = self.relief()
        proof = wf.learn_relief(self.path, 'agent-2', g, c)
        with closing(storage._connect(self.path)) as db:
            db.execute('DELETE FROM development_records WHERE id=?', (proof['record_id'],))
            db.commit()
        with self.assertRaises(ValueError):
            wf.choose_goal(self.path, 'agent-2')

    def test_unproved_location_input_is_rejected_before_native_movement(self):
        head = storage.inspect(self.path)['state_hash']
        with self.assertRaisesRegex(ValueError, 'unproved location'):
            wf.acquire(self.path, 'agent-2', 'water', 'drink', {'location': 'forged', 'record_id': None})
        self.assertEqual(storage.inspect(self.path)['state_hash'], head)

    def test_own_need_uses_actual_report_then_persists_native_confirmation(self):
        g, c = self.relief()
        wf.learn_relief(self.path, 'agent-2', g, c)
        wf.walk(self.path, 'agent-1', [14, 3])
        wf.walk(self.path, 'agent-2', [13, 3])
        wf.remember_site(self.path, 'agent-2')
        token = wf.coin_site(self.path, 'agent-1')
        dev.execute(self.path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)
        wf.learn_site(self.path, 'agent-2', 'agent-1')
        wf.walk(self.path, 'agent-2', [6, 6])
        o = dev.own_observation(self.path, 'agent-1')
        teaching.intervene(self.path, dict(schema_version=1, run_id=o['run_id'], branch_id=o['run_id'],
            intervention_id='add-test-water', observation_version=o['observation_version'], kind='introduce_object',
            parameters=dict(entity_id='test-water', x_m=14, y_m=3, material='water', mass_kg=.05, energy_j=0)))
        wf.observe_source(self.path, 'agent-1')
        wf.walk(self.path, 'agent-1', [2, 3])
        dev.execute(self.path, 'agent-2', 'rest', duration=60, update_memory=False)
        wf.send(self.path, 'agent-1')
        result = wf.policy_step(self.path, 'agent-2')
        self.assertTrue(result['used_information'])
        self.assertTrue(result['execution']['goal_completed'])
        self.assertFalse(result['execution']['assigned'])
        self.assertTrue(result['execution']['report_confirmed'])
        self.assertEqual(result['execution']['confirmation']['status'], 'confirmed_by_own_native_acquisition_and_consumption')
        self.assertEqual(result['execution']['source'], 'test-water')
        self.assertTrue(wf.audit(self.path))

    def test_empty_source_prevents_native_invalid_gather(self):
        wf.walk(self.path, 'agent-2', [13, 3])
        before = wf.private(self.path, 'agent-2', 'agent-2')
        result = wf.acquire(self.path, 'agent-2', 'water', 'drink')
        self.assertFalse(result['goal_completed'])
        self.assertEqual(result['actions'], [])
        self.assertEqual(wf.private(self.path, 'agent-2', 'agent-2'), before)

    def test_missing_native_speech_proof_stops_audit(self):
        self.speech()
        proof = wf.learn_site(self.path, 'agent-2', 'agent-1')
        with closing(storage._connect(self.path)) as db:
            db.execute('DELETE FROM events WHERE seq=?', (int(proof['message']['source_event_seq']),))
            db.commit()
        with self.assertRaises(ValueError):
            wf.audit(self.path)

    def test_saved_learner_retains_own_state_and_archive_snapshot(self):
        self.speech()
        wf.learn_site(self.path, 'agent-2', 'agent-1')
        before = wf.audit(self.path)
        backup = Path(self.tmp.name) / 'backup.sqlite'
        storage.save(self.path, 'persistent-h4', backup)
        self.assertEqual(wf.audit(backup), before)
        dev.archive(self.path)
        self.assertEqual(wf.audit(self.path), before)


if __name__ == '__main__':
    unittest.main()
