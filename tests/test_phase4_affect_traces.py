from contextlib import closing
from pathlib import Path
import json
import tempfile
import unittest

from underworld import life_phase1 as phase1
from underworld import life_phase2 as phase2
from underworld import life_phase3 as phase3
from underworld import life_phase4 as phase4
from underworld import life_store, weather_store


class Phase4AffectTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'
        self.phase1_db = root / 'phase1.sqlite'
        self.phase2_db = root / 'phase2.sqlite'
        self.phase3_db = root / 'phase3.sqlite'
        self.phase4_db = root / 'phase4.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)
        phase1.attach(self.source, self.phase1_db)
        phase2.attach(self.phase1_db, self.phase2_db)
        phase3.attach(self.phase2_db, self.phase3_db)

    def test_attach_persists_private_affect_traces_and_preserves_upstream(self):
        source_bytes = self.phase3_db.read_bytes()
        result = phase4.attach(self.phase3_db, self.phase4_db)
        self.assertEqual(source_bytes, self.phase3_db.read_bytes())
        self.assertEqual(result['affect_trace_count'], 2)
        trace = phase4.affect_traces(self.phase4_db, agent_id='agent-1')[0]
        self.assertEqual(trace['privacy_scope'], 'private')
        self.assertEqual(trace['provenance'], 'derived')
        self.assertEqual(trace['explanation_status'], 'unavailable')
        self.assertEqual(trace['tick_before'], trace['tick_after'])
        self.assertTrue(phase4.replay(self.phase4_db)['phase4_verified'])

    def test_capture_is_append_only_and_idempotent_at_same_native_state(self):
        phase4.attach(self.phase3_db, self.phase4_db)
        before = life_store.inspect(self.phase4_db)
        life_store.commit(self.phase4_db, {'kind': 'emotion-policy', 'agent': 'agent-1'}, 'phase4-policy')
        first = phase4.capture(self.phase4_db, agents=['agent-1'])
        second = phase4.capture(self.phase4_db, agents=['agent-1'])
        self.assertEqual(len(first['captured_affect_trace_ids']), 1)
        self.assertEqual(second['captured_affect_trace_ids'], [])
        self.assertEqual(first['affect_trace_count'], 3)
        self.assertEqual(second['affect_trace_count'], 3)
        self.assertGreater(life_store.inspect(self.phase4_db)['operations'], before['operations'])
        self.assertTrue(phase4.replay(self.phase4_db)['phase4_verified'])

    def test_invalid_owner_and_tampering_fail_closed(self):
        phase4.attach(self.phase3_db, self.phase4_db)
        with self.assertRaisesRegex(ValueError, 'enrolled'):
            phase4.capture(self.phase4_db, agents=['agent-9'])
        with closing(weather_store.connect(self.phase4_db, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT affect_trace_id,payload FROM phase4_affect_traces LIMIT 1').fetchone()
            trace_id, payload = row
            record = json.loads(payload)
            record['fast_affect']['valence'] = .9
            db.execute('UPDATE phase4_affect_traces SET payload=? WHERE affect_trace_id=?',
                       (json.dumps(record, sort_keys=True, separators=(',', ':')), trace_id))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            phase4.replay(self.phase4_db)

    def test_requires_phase3_and_backup_replays(self):
        with self.assertRaisesRegex(ValueError, 'Phase-3 destination'):
            phase4.attach(self.phase2_db, self.phase4_db)
        phase4.attach(self.phase3_db, self.phase4_db)
        backup = Path(self.tmp.name) / 'phase4-backup.sqlite'
        phase4.save(self.phase4_db, backup)
        self.assertTrue(phase4.replay(backup)['phase4_verified'])


if __name__ == '__main__':
    unittest.main()
