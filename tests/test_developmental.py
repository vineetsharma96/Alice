from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import developmental as dev, storage, runtime

ROOT = Path(__file__).resolve().parents[1]


class DevelopmentalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'world.sqlite'
        dev.initialize(self.path, seed=41)

    def probe(self, target='resource-1', learn=True, **kwargs):
        return dev.execute(self.path, 'agent-1', 'gather', [target], {'mass_kg': .001},
                           learn_food=learn, **kwargs)

    def test_initial_manifest_and_private_empty_tables(self):
        value = dev.audit(self.path)
        for state in value['people'].values():
            self.assertEqual(state['associations'], {})
            self.assertEqual(state['production'], {})
            self.assertEqual(state['comprehension'], {})
            self.assertEqual(state['procedures'], [])
        self.assertIn('sensory', value['meta']['priors'])
        with self.assertRaisesRegex(ValueError, 'private learner access denied'):
            dev.private_state(self.path, 'agent-2', 'agent-1')

    def test_native_experience_changes_reusable_prediction_and_choice(self):
        self.probe()
        self.probe('resource-2')
        choice = dev.choose(self.path, 'agent-1', ['resource-1','resource-2'])
        self.assertEqual(choice['target'], 'resource-1')
        p = {p['target']:p['mean'] for p in choice['predictions']}
        self.assertGreater(p['resource-1'], p['resource-2'])
        self.assertGreater(self.probe()['food_gain_ug'], 0)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_frozen_evaluation_does_not_update_tables(self):
        self.probe()
        before = dev.private_state(self.path, 'agent-1', 'agent-1')
        self.probe(learn=False, update_memory=False)
        after = dev.private_state(self.path, 'agent-1', 'agent-1')
        self.assertEqual(before['associations'], after['associations'])
        self.assertEqual(before['objects'], after['objects'])
        self.assertEqual(after['experiences'], before['experiences']+1)

    def test_native_rejections_remain_distinct(self):
        a = self.probe('resource-3')
        b = self.probe('resource-4')
        self.assertEqual(a['outcome_category'], 'OUT_OF_REACH')
        self.assertEqual(b['outcome_category'], 'TARGET_UNAVAILABLE')
        self.assertFalse(a['goal_success'])
        self.assertFalse(b['goal_success'])

    def test_crash_after_physical_commit_reconciles_once(self):
        def fault(stage):
            if stage == 'after_native_commit':
                raise RuntimeError('crash')
        with self.assertRaisesRegex(RuntimeError, 'crash'):
            self.probe(fault=fault)
        physical = storage.inspect(self.path)['state_hash']
        result = dev.reconcile(self.path, 'agent-1')
        self.assertTrue(result['goal_success'])
        self.assertIsNone(dev.reconcile(self.path, 'agent-1'))
        self.assertEqual(storage.inspect(self.path)['state_hash'], physical)
        self.assertEqual(dev.private_state(self.path, 'agent-1', 'agent-1')['experiences'], 1)

    def test_crash_before_update_commit_rolls_back_learning_only(self):
        def fault(stage):
            if stage == 'before_update_commit':
                raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            self.probe(fault=fault)
        self.assertEqual(dev.private_state(self.path, 'agent-1', 'agent-1')['experiences'], 0)
        dev.reconcile(self.path, 'agent-1')
        self.assertEqual(dev.private_state(self.path, 'agent-1', 'agent-1')['experiences'], 1)

    def test_inflight_resume_never_resubmits_native_request(self):
        def fault(stage):
            if stage == 'after_reservation':
                raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            dev.execute(self.path, 'agent-1', 'rest', duration=3, fault=fault)
        with closing(storage._connect(self.path, readonly=True)) as db:
            pending = dev._read(db, 'development_pending', 'agent-1', 'agent')
        storage.advance(self.path, 1, [(0,pending['request'])])
        result = dev.reconcile(self.path, 'agent-1')
        self.assertEqual(result['receipt']['status'], 'completed')
        with closing(storage._connect(self.path, readonly=True)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM decisions').fetchone()[0], 1)

    def test_missing_evidence_becomes_uncertain(self):
        self.probe()
        with closing(storage._connect(self.path)) as db:
            db.execute('DELETE FROM development_records')
        p = dev.choose(self.path, 'agent-1', ['resource-1'])['predictions'][0]
        self.assertTrue(p['uncertain_missing_source'])
        self.assertEqual(p['mean'], .5)
        with self.assertRaisesRegex(ValueError, 'history missing'):
            dev.audit(self.path)

    def test_fresh_process_backup_retains_private_state(self):
        self.probe()
        backup = self.path.parent/'saved.sqlite'
        storage.save(self.path, 'h-resume', backup)
        child = subprocess.run([sys.executable, '-m', 'underworld.developmental','status','--db',str(backup)],
                               cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(json.loads(child.stdout)['people'], dev.audit(self.path)['people'])

    def test_archive_preserves_recoverable_experience_and_missing_archive_refuses(self):
        self.probe()
        dev.archive(self.path)
        self.assertEqual(dev.audit(self.path)['record_counts']['agent-1'], 1)
        files = list(Path(str(self.path)+'.epochs').glob('*.sqlite'))
        self.assertTrue(files)
        # Native action events retained here can still prove the copied receipt;
        # archive integrity itself remains a separate required resume guard.
        runtime.verify_archives(self.path)
        files[0].write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            runtime.verify_archives(self.path)
        with self.assertRaises(ValueError):
            dev.private_state(self.path, 'agent-1', 'agent-1')

    def test_experiences_survive_beyond_recent_episode_lookup(self):
        first = self.probe()
        for _ in range(65):
            dev.execute(self.path, 'agent-1', 'rest')
        self.assertEqual(dev.audit(self.path)['record_counts']['agent-1'], 66)
        with closing(storage._connect(self.path, readonly=True)) as db:
            proof = json.loads(db.execute('SELECT payload FROM development_records WHERE id=?',
                                         (first['request']['request_id'],)).fetchone()[0])
        self.assertEqual(proof['native_events'], first['native_events'])

    def test_orphan_archive_is_not_used_as_native_proof(self):
        first = self.probe()
        directory = Path(str(self.path)+'.epochs')
        directory.mkdir()
        storage.save(self.path, 'unregistered', directory/'unregistered.sqlite')
        with closing(storage._connect(self.path)) as db:
            for reference in first['receipt']['event_refs']:
                db.execute('DELETE FROM events WHERE seq=?', (int(reference),))
        prediction = dev.choose(self.path, 'agent-1', ['resource-1'])['predictions'][0]
        self.assertTrue(prediction['uncertain_missing_source'])

    def test_interrupted_archive_rejects_same_native_head_with_changed_learning_state(self):
        self.probe()
        def fault(stage, tick):
            if stage == 'after_checkpoint':
                raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            dev.archive(self.path, fault=fault)
        physical = storage.inspect(self.path)['state_hash']
        dev.choose(self.path, 'agent-1', ['resource-1'])  # Only private RNG changes.
        self.assertEqual(storage.inspect(self.path)['state_hash'], physical)
        with self.assertRaisesRegex(ValueError, 'different developmental state'):
            dev.archive(self.path)
        self.assertEqual(storage.inspect(self.path)['state_hash'], physical)

    def test_archival_refuses_unreconciled_learner_intent(self):
        def fault(stage):
            if stage == 'after_reservation':
                raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            self.probe(fault=fault)
        with self.assertRaisesRegex(ValueError, 'pending intents'):
            dev.archive(self.path)

    def test_archive_eviction_cannot_destroy_a_learning_source(self):
        config = dev.load(ROOT/'config/developmental.toml')
        config['logging']['event_retention_count'] = 4
        self.path = self.path.parent/'short-history.sqlite'
        dev.initialize(self.path, config=config)
        self.probe()
        dev.archive(self.path)
        for _ in range(2):
            storage.advance(self.path, 8)
            dev.archive(self.path)
        storage.advance(self.path, 8)
        with self.assertRaisesRegex(ValueError, 'protected source archive quota'):
            dev.archive(self.path)
        self.assertEqual(dev.audit(self.path)['record_counts']['agent-1'], 1)


if __name__ == '__main__':
    unittest.main()
