from contextlib import closing
from pathlib import Path
import json
import tempfile
import unittest

from underworld import life_phase1 as phase1
from underworld import life_phase2 as phase2
from underworld import life_phase3 as phase3
from underworld import life_store, weather_store


class Phase3BodyNeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'
        self.phase1_db = root / 'phase1.sqlite'
        self.phase2_db = root / 'phase2.sqlite'
        self.phase3_db = root / 'phase3.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)
        phase1.attach(self.source, self.phase1_db)
        phase2.attach(self.phase1_db, self.phase2_db)

    def test_attach_persists_native_body_snapshots_and_preserves_upstream(self):
        source_bytes = self.phase2_db.read_bytes()
        result = phase3.attach(self.phase2_db, self.phase3_db)
        self.assertEqual(source_bytes, self.phase2_db.read_bytes())
        self.assertEqual(result['body_need_count'], 2)
        records = phase3.body_needs(self.phase3_db, agent_id='agent-1')
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record['privacy_scope'], 'private')
        self.assertEqual(record['provenance'], 'native')
        self.assertEqual(record['source_event_ids'], [record['source_event_ids'][0]])
        self.assertTrue(phase3.replay(self.phase3_db)['phase3_verified'])

    def test_capture_is_sidecar_only_and_idempotent_at_same_native_state(self):
        phase3.attach(self.phase2_db, self.phase3_db)
        before = life_store.inspect(self.phase3_db)
        life_store.commit(self.phase3_db, {'kind': 'step', 'ticks': 1}, 'phase3-native-step')
        first = phase3.capture(self.phase3_db, agents=['agent-1'])
        second = phase3.capture(self.phase3_db, agents=['agent-1'])
        self.assertEqual(len(first['captured_body_need_ids']), 1)
        self.assertEqual(second['captured_body_need_ids'], [])
        self.assertEqual(first['body_need_count'], 3)
        self.assertEqual(second['body_need_count'], 3)
        self.assertGreater(life_store.inspect(self.phase3_db)['snapshot']['tick'], before['snapshot']['tick'])
        self.assertEqual(len(phase3.body_needs(self.phase3_db, agent_id='agent-1')), 2)
        self.assertTrue(phase3.replay(self.phase3_db)['phase3_verified'])

    def test_invalid_owner_and_tampering_fail_closed(self):
        phase3.attach(self.phase2_db, self.phase3_db)
        with self.assertRaisesRegex(ValueError, 'enrolled'):
            phase3.capture(self.phase3_db, agents=['agent-9'])
        with closing(weather_store.connect(self.phase3_db, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body_need_id,payload FROM phase3_body_needs LIMIT 1').fetchone()
            body_need_id, payload = row
            record = json.loads(payload)
            record['hunger'] = .99
            db.execute('UPDATE phase3_body_needs SET payload=? WHERE body_need_id=?',
                       (json.dumps(record, sort_keys=True, separators=(',', ':')), body_need_id))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            phase3.replay(self.phase3_db)

    def test_requires_phase2_and_backup_replays(self):
        with self.assertRaisesRegex(ValueError, 'Phase-2 destination'):
            phase3.attach(self.phase1_db, self.phase3_db)
        phase3.attach(self.phase2_db, self.phase3_db)
        backup = Path(self.tmp.name) / 'phase3-backup.sqlite'
        phase3.save(self.phase3_db, backup)
        self.assertTrue(phase3.replay(backup)['phase3_verified'])


if __name__ == '__main__':
    unittest.main()
