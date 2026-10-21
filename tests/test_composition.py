from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import composition as comp, developmental as dev, storage, wayfinding as wf
from scripts.composition_study import train

ROOT = Path(__file__).resolve().parents[1]


class CompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = tempfile.TemporaryDirectory()
        cls.base = Path(cls.suite.name) / 'trained.sqlite'
        cls.training = train(cls.base, 47)

    @classmethod
    def tearDownClass(cls):
        cls.suite.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'world.sqlite'
        storage.save(self.base, self._testMethodName, self.path)

    def test_parser_refuses_unbounded_duplicate_and_malformed_signals(self):
        for text in ('', 's00 s01 s02', 's00 s00', 's10', 's00\ns01', 'hello', 's00  s01'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                comp.parse(text)
        self.assertEqual(comp.parse('s0f s00'), ['s0f', 's00'])

    def test_private_access_and_unseen_factor_refusal(self):
        with self.assertRaisesRegex(ValueError, 'private H5'):
            comp.private(self.path, 'agent-1', 'agent-2')
        with self.assertRaisesRegex(ValueError, 'unknown private factor'):
            comp.encode(self.path, 'agent-2', self.training['ids'][0])
        with self.assertRaisesRegex(ValueError, 'own visible'):
            comp.encode(self.path, 'agent-1', 'secret-resource', True)

    def test_heldout_combinations_reuse_learned_parts_without_updates(self):
        before = comp.audit(self.path)['h5_memory_hashes']
        for i, target in enumerate(self.training['heldout']):
            seq = max(int(r['source_event_seq']) for r in dev.own_observation(self.path, 'agent-2')['audible_reports'])
            text = comp.encode(self.path, 'agent-1', target)
            comp.send(self.path, 'agent-1', f'heldout-{i}', text)
            chosen = comp.select(self.path, 'agent-2', 'agent-1', self.training['ids'], seq)
            self.assertEqual(chosen['target'], target)
        self.assertEqual(comp.audit(self.path)['h5_memory_hashes'], before)

    def test_logical_message_recovery_at_all_commit_boundaries(self):
        for stage in ('after_message_intent', 'after_reservation', 'after_native_commit', 'before_update_commit', 'after_update_commit'):
            with self.subTest(stage=stage):
                text = comp.encode(self.path, 'agent-1', self.training['ids'][0])
                def crash(actual):
                    if actual == stage:
                        raise RuntimeError(stage)
                with self.assertRaises(RuntimeError):
                    comp.send(self.path, 'agent-1', stage, text, crash)
                result = comp.send(self.path, 'agent-1', stage, text)
                state = comp.audit(self.path)
                head = storage.inspect(self.path)['state_hash']
                self.assertEqual(comp.send(self.path, 'agent-1', stage, text), result)
                self.assertEqual(comp.audit(self.path), state)
                self.assertEqual(storage.inspect(self.path)['state_hash'], head)
                with closing(storage._connect(self.path, readonly=True)) as db:
                    count = db.execute("SELECT COUNT(*) FROM decisions WHERE json_extract(request,'$.request_id')=?", (result['request_id'],)).fetchone()[0]
                    self.assertEqual(count, 1)
                with self.assertRaisesRegex(ValueError, 'conflicting H5'):
                    comp.send(self.path, 'agent-1', stage, 's00' if text != 's00' else 's01')

    def test_unsubmitted_message_at_changed_head_refuses_reexecution(self):
        def crash(stage):
            raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):
            comp.send(self.path, 'agent-1', 'stale', 's00', crash)
        dev.execute(self.path, 'agent-2', 'rest', update_memory=False)
        with self.assertRaisesRegex(ValueError, 'changed head'):
            comp.send(self.path, 'agent-1', 'stale', 's00')

    def lesson(self, name):
        target = self.training['ids'][0]
        point = next(e['position_m'] for e in dev.own_observation(self.path, 'agent-1')['visible_entities'] if e['entity_id'] == target)
        wf.walk(self.path, 'agent-1', point)
        comp.begin(self.path, 'agent-2', name, self.training['ids'])
        dev.execute(self.path, 'agent-1', 'deposit', [target], {'mass_kg': .001}, update_memory=False)
        comp.send(self.path, 'agent-1', name, comp.encode(self.path, 'agent-1', target))

    def test_learning_before_and_after_commit_is_exactly_once(self):
        for stage in ('before_learning_commit', 'after_learning_commit'):
            self.lesson(stage)
            n = comp.private(self.path, 'agent-2', 'agent-2')['external_teaching']
            def crash(actual):
                if actual == stage:
                    raise RuntimeError(stage)
            with self.assertRaises(RuntimeError):
                comp.learn(self.path, 'agent-2', 'agent-1', stage, crash)
            result = comp.learn(self.path, 'agent-2', 'agent-1', stage)
            expected = n + 1
            self.assertEqual(comp.private(self.path, 'agent-2', 'agent-2')['external_teaching'], expected)
            state = comp.audit(self.path)
            self.assertEqual(comp.learn(self.path, 'agent-2', 'agent-1', stage), result)
            self.assertEqual(comp.audit(self.path), state)
            with self.assertRaisesRegex(ValueError, 'conflicting H5'):
                comp.learn(self.path, 'agent-2', 'agent-3', stage)

    def test_no_physical_demonstration_means_no_learning(self):
        comp.begin(self.path, 'agent-2', 'no-deposit', self.training['ids'])
        comp.send(self.path, 'agent-1', 'no-deposit', 's00 s01')
        with self.assertRaisesRegex(ValueError, 'exactly one native'):
            comp.learn(self.path, 'agent-2', 'agent-1', 'no-deposit')

    def test_fresh_process_continues_pending_native_message_once(self):
        def crash(stage):
            if stage == 'after_native_commit':
                raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):
            comp.send(self.path, 'agent-1', 'fresh', 's00 s01', crash)
        code = 'from underworld import composition as c; import sys,json; print(json.dumps(c.send(sys.argv[1],"agent-1","fresh","s00 s01")))'
        child = subprocess.run([sys.executable, '-c', code, str(self.path)], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(json.loads(child.stdout), comp.send(self.path, 'agent-1', 'fresh', 's00 s01'))
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_save_archive_and_missing_archive_protection(self):
        before = comp.audit(self.path)
        backup = self.path.parent / 'backup.sqlite'
        storage.save(self.path, 'h5-backup', backup)
        self.assertEqual(comp.audit(backup), before)
        dev.archive(self.path)
        self.assertEqual(comp.audit(self.path), before)
        epochs = list(Path(str(self.path) + '.epochs').glob('*.sqlite'))
        self.assertTrue(epochs)
        epochs[0].rename(epochs[0].with_suffix('.missing'))
        with self.assertRaises((ValueError, OSError)):
            comp.audit(self.path)

    def test_proof_tampering_and_budget_overflow_fail_closed(self):
        with closing(storage._connect(self.path)) as db:
            state = dev._person(db, 'agent-2', 'agent-2')
            next(iter(state['h5']['hypotheses'].values()))['n'] += 1
            dev._put(db, 'development_people', 'agent-2', state)
            db.commit()
        with self.assertRaisesRegex(ValueError, 'disagree|proof count'):
            comp.audit(self.path)
        with closing(storage._connect(self.path)) as db:
            state = dev._person(db, 'agent-2', 'agent-2')
            state['h5']['hypotheses'] = {str(i): {} for i in range(65)}
            dev._put(db, 'development_people', 'agent-2', state)
            db.commit()
        with self.assertRaisesRegex(ValueError, 'budget'):
            comp.private(self.path, 'agent-2', 'agent-2')

    def test_decision_refuses_missing_native_learning_source(self):
        text = comp.encode(self.path, 'agent-1', self.training['heldout'][0])
        comp.send(self.path, 'agent-1', 'missing-proof', text)
        h = comp.private(self.path, 'agent-2', 'agent-2')
        ident = next(iter(h['hypotheses'].values()))['evidence'][0]
        with closing(storage._connect(self.path)) as db:
            proof = dev._read(db, 'development_records', ident, 'id')
            for seq in proof['native_events']:
                db.execute('DELETE FROM events WHERE seq=?', (int(seq),))
            db.commit()
        with self.assertRaises(ValueError):
            comp.select(self.path, 'agent-2', 'agent-1', self.training['ids'])


if __name__ == '__main__':
    unittest.main()
