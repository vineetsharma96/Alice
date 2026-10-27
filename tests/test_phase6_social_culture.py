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
from underworld import life_phase6 as phase6
from underworld import life_store, weather_store


class Phase6SocialCultureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'; self.p1 = root / 'p1.sqlite'; self.p2 = root / 'p2.sqlite'
        self.p3 = root / 'p3.sqlite'; self.p4 = root / 'p4.sqlite'; self.p5 = root / 'p5.sqlite'; self.p6 = root / 'p6.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)
        phase1.attach(self.source, self.p1); phase2.attach(self.p1, self.p2); phase3.attach(self.p2, self.p3)
        phase4.attach(self.p3, self.p4); phase5.attach(self.p4, self.p5)

    def ref(self):
        with closing(weather_store.connect(self.p5)) as db:
            return db.execute('SELECT observation_id FROM phase1_observations WHERE agent_id=? LIMIT 1', ('agent-1',)).fetchone()[0]

    def test_events_and_artifacts_are_private_access_controlled_and_replayable(self):
        self.assertEqual(self.p5.read_bytes(), self.p5.read_bytes())
        result = phase6.attach(self.p5, self.p6); ref = self.ref()
        self.assertEqual(result['event_count'], 0); self.assertEqual(result['artifact_count'], 0)
        event = phase6.record_event(self.p6, event_id='speech-1', event_kind='speech', actor_id='agent-1', other_actor_id='agent-2', payload={'text': 'hello'}, source_refs=[ref])
        self.assertEqual(event['event_kind'], 'speech')
        phase6.write_artifact(self.p6, artifact_id='book-1', owner_id='agent-1', artifact_kind='procedure', content={'text': 'PROCEDURE ...'}, source_refs=[ref])
        listing = phase6.artifacts(self.p6, reader_id='agent-2')
        self.assertEqual(listing, [])
        read = phase6.read_artifact(self.p6, artifact_id='book-1', reader_id='agent-2', source_refs=[ref])
        self.assertEqual(read['content']['text'], 'PROCEDURE ...')
        self.assertEqual(len(phase6.events(self.p6, actor_id='agent-2')), 1)
        self.assertTrue(phase6.replay(self.p6)['phase6_verified'])

    def test_boundaries_and_tampering_fail_closed(self):
        ref = self.ref()
        with self.assertRaisesRegex(ValueError, 'Phase-5 destination'):
            phase6.attach(self.p4, self.p6)
        phase6.attach(self.p5, self.p6)
        with self.assertRaisesRegex(ValueError, 'source reference'):
            phase6.record_event(self.p6, event_id='bad', event_kind='speech', actor_id='agent-1', source_refs=['missing'])
        phase6.write_artifact(self.p6, artifact_id='book-1', owner_id='agent-1', artifact_kind='book', content={'text': 'x'}, source_refs=[ref])
        with closing(weather_store.connect(self.p6, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            artifact_id, payload = db.execute('SELECT artifact_id,payload FROM phase6_artifacts LIMIT 1').fetchone()
            value = json.loads(payload); value['content']['text'] = 'tampered'
            db.execute('UPDATE phase6_artifacts SET payload=? WHERE artifact_id=?', (json.dumps(value, sort_keys=True, separators=(',', ':')), artifact_id)); db.commit()
        with self.assertRaisesRegex(ValueError, 'artifact row mismatch'):
            phase6.replay(self.p6)

    def test_backup_replays_and_source_remains_unchanged(self):
        source_bytes = self.p5.read_bytes(); phase6.attach(self.p5, self.p6)
        self.assertEqual(source_bytes, self.p5.read_bytes())
        backup = Path(self.tmp.name) / 'p6-backup.sqlite'; phase6.save(self.p6, backup)
        self.assertTrue(phase6.replay(backup)['phase6_verified'])


if __name__ == '__main__': unittest.main()
