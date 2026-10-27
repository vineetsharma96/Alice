from contextlib import closing
from pathlib import Path
import json
import tempfile
import unittest

from underworld import life_phase1 as phase1
from underworld import life_phase2 as phase2
from underworld import life_phase3 as phase3
from underworld import life_phase4 as phase4
from underworld import life_phase5 as phase5
from underworld import life_store, weather_store


class Phase5UnifiedProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'
        self.phase1_db = root / 'phase1.sqlite'
        self.phase2_db = root / 'phase2.sqlite'
        self.phase3_db = root / 'phase3.sqlite'
        self.phase4_db = root / 'phase4.sqlite'
        self.phase5_db = root / 'phase5.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)
        phase1.attach(self.source, self.phase1_db)
        phase2.attach(self.phase1_db, self.phase2_db)
        phase3.attach(self.phase2_db, self.phase3_db)
        phase4.attach(self.phase3_db, self.phase4_db)

    def test_attach_creates_complete_cross_subsystem_lineage_without_touching_source(self):
        source_bytes = self.phase4_db.read_bytes()
        result = phase5.attach(self.phase4_db, self.phase5_db)
        self.assertEqual(source_bytes, self.phase4_db.read_bytes())
        self.assertEqual(result['snapshot_count'], 2)
        entries = phase5.snapshots(self.phase5_db, agent_id='agent-1')
        self.assertEqual(len(entries), 1)
        record = entries[0]['record']
        self.assertEqual(record['profile'], 'ALICE-LIFE-2')
        self.assertEqual(record['identity']['agent_id'], 'agent-1')
        self.assertEqual(record['observation']['checksum'].__class__, str)
        self.assertEqual(record['body_need']['checksum'].__class__, str)
        self.assertEqual(record['affect_trace']['checksum'].__class__, str)
        self.assertTrue(phase5.replay(self.phase5_db)['phase5_verified'])

    def test_capture_is_idempotent_and_links_new_native_tick(self):
        phase5.attach(self.phase4_db, self.phase5_db)
        life_store.commit(self.phase5_db, {'kind': 'step', 'ticks': 1}, 'phase5-native-step')
        first = phase5.capture(self.phase5_db, agents=['agent-1'])
        second = phase5.capture(self.phase5_db, agents=['agent-1'])
        self.assertEqual(len(first['captured_snapshot_ids']), 1)
        self.assertEqual(second['captured_snapshot_ids'], [])
        self.assertEqual(first['snapshot_count'], 3)
        self.assertEqual(second['snapshot_count'], 3)
        records = phase5.snapshots(self.phase5_db, agent_id='agent-1')
        self.assertEqual([item['record']['native_tick'] for item in records], [0, 1])
        self.assertTrue(phase5.replay(self.phase5_db)['phase5_verified'])

    def test_tampered_lineage_and_wrong_upstream_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Phase-4 destination'):
            phase5.attach(self.phase3_db, self.phase5_db)
        phase5.attach(self.phase4_db, self.phase5_db)
        with closing(weather_store.connect(self.phase5_db, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            snapshot_id, payload = db.execute('SELECT snapshot_id,payload FROM phase5_snapshots LIMIT 1').fetchone()
            record = json.loads(payload)
            record['body_need']['checksum'] = '0' * 64
            db.execute('UPDATE phase5_snapshots SET payload=? WHERE snapshot_id=?',
                       (json.dumps(record, sort_keys=True, separators=(',', ':')), snapshot_id))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'lineage checksum mismatch'):
            phase5.replay(self.phase5_db)

    def test_backup_is_new_copy_and_replays(self):
        phase5.attach(self.phase4_db, self.phase5_db)
        backup = Path(self.tmp.name) / 'phase5-backup.sqlite'
        phase5.save(self.phase5_db, backup)
        self.assertTrue(phase5.replay(backup)['phase5_verified'])
        self.assertEqual(phase5.inspect(backup)['snapshot_count'], 2)


if __name__ == '__main__':
    unittest.main()
