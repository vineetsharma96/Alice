from contextlib import closing
from pathlib import Path
import json
import tempfile
import unittest

from underworld import life_phase1 as phase1
from underworld import life_store, weather_store


class Phase1PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'
        self.destination = root / 'life-phase1.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)

    def test_attach_persists_identity_and_private_observation_without_touching_source(self):
        source_bytes = self.source.read_bytes()
        result = phase1.attach(self.source, self.destination)
        self.assertEqual(source_bytes, self.source.read_bytes())
        self.assertEqual(result['profile'], 'ALICE-LIFE-2')
        self.assertEqual(result['identity_count'], 2)
        self.assertEqual(result['observation_count'], 2)
        self.assertEqual(result['operation_count'], 2)
        self.assertEqual([r['agent_id'] for r in phase1.identities(self.destination)], ['agent-1', 'agent-2'])
        records = phase1.observations(self.destination, agent_id='agent-1')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['privacy_scope'], 'private')
        self.assertEqual(records[0]['provenance'], 'native')
        self.assertTrue(phase1.replay(self.destination)['verified'])
        with closing(weather_store.connect(self.source)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertFalse({'phase1_meta', 'phase1_identity', 'phase1_observations'} & tables)

    def test_capture_is_readable_idempotent_and_does_not_rewrite_native_source(self):
        phase1.attach(self.source, self.destination)
        before = life_store.inspect(self.destination)
        life_store.commit(self.destination, {'kind': 'step', 'ticks': 1}, 'phase1-native-step')
        first = phase1.capture(self.destination, agents=['agent-1'])
        second = phase1.capture(self.destination, agents=['agent-1'])
        self.assertEqual(len(first['captured_observation_ids']), 1)
        self.assertEqual(second['captured_observation_ids'], [])
        self.assertEqual(first['observation_count'], 3)
        self.assertEqual(second['observation_count'], 3)
        self.assertGreater(life_store.inspect(self.destination)['snapshot']['tick'], before['snapshot']['tick'])
        self.assertEqual(len(phase1.observations(self.destination, agent_id='agent-1')), 2)
        self.assertTrue(phase1.replay(self.destination)['verified'])

    def test_new_destination_and_tamper_boundaries_fail_closed(self):
        phase1.attach(self.source, self.destination)
        with self.assertRaisesRegex(ValueError, 'NEW path'):
            phase1.attach(self.source, self.destination)
        with closing(weather_store.connect(self.destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            payload = db.execute('SELECT payload FROM phase1_observations LIMIT 1').fetchone()[0]
            tampered = json.loads(payload)
            tampered['own_state']['tampered'] = True
            db.execute('UPDATE phase1_observations SET payload=? WHERE seq=1',
                       (json.dumps(tampered, sort_keys=True, separators=(',', ':')),))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            phase1.replay(self.destination)

    def test_phase1_backup_is_new_copy(self):
        phase1.attach(self.source, self.destination)
        backup = Path(self.tmp.name) / 'phase1-backup.sqlite'
        result = phase1.save(self.destination, backup)
        self.assertEqual(result['observation_count'], 2)
        self.assertEqual(phase1.replay(backup)['observations'], 2)
        self.assertEqual(self.destination.read_bytes(), self.destination.read_bytes())

    def test_attach_from_existing_alice_life_copy_preserves_source(self):
        life_copy = Path(self.tmp.name) / 'life1.sqlite'
        destination = Path(self.tmp.name) / 'phase1-from-life.sqlite'
        life_store.attach(self.source, life_copy)
        source_bytes = life_copy.read_bytes()
        result = phase1.attach(life_copy, destination, agents=['agent-2'])
        self.assertEqual(source_bytes, life_copy.read_bytes())
        self.assertEqual(result['actors'], ['agent-2'])
        self.assertEqual(result['identity_count'], 1)
        self.assertTrue(phase1.replay(destination)['verified'])


if __name__ == '__main__':
    unittest.main()
