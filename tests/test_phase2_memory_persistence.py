from contextlib import closing
from pathlib import Path
import json
import tempfile
import unittest

from underworld import life_phase1 as phase1
from underworld import life_phase2 as phase2
from underworld import life_store, weather_store


class Phase2MemoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / 'source.sqlite'
        self.phase1_db = root / 'phase1.sqlite'
        self.phase2_db = root / 'phase2.sqlite'
        life_store.initialize_source(self.source, seed=61, population=2)
        phase1.attach(self.source, self.phase1_db)

    def source_ref(self):
        with closing(weather_store.connect(self.phase1_db)) as db:
            return db.execute('SELECT observation_id FROM phase1_observations WHERE agent_id=? ORDER BY seq LIMIT 1',
                              ('agent-1',)).fetchone()[0]

    def test_attach_and_write_memory_preserve_phase1_and_native_source(self):
        source_bytes = self.source.read_bytes()
        phase1_bytes = self.phase1_db.read_bytes()
        result = phase2.attach(self.phase1_db, self.phase2_db)
        self.assertEqual(source_bytes, self.source.read_bytes())
        self.assertEqual(phase1_bytes, self.phase1_db.read_bytes())
        self.assertEqual(result['memory_count'], 0)
        memory = phase2.write_memory(
            self.phase2_db, agent_id='agent-1', memory_id='memory-1',
            memory_kind='episode', content={'text': 'saw the meadow'},
            source_refs=[self.source_ref()], confidence=.8, salience=.7)
        self.assertEqual(memory['record']['privacy_scope'], 'private')
        self.assertEqual(memory['effective_validity'], 'active')
        self.assertEqual(phase2.inspect(self.phase2_db)['memory_count'], 1)
        replay = phase2.replay(self.phase2_db)
        self.assertTrue(replay['verified'])
        self.assertTrue(replay['phase2_verified'])

    def test_corrections_and_invalidation_are_append_only(self):
        phase2.attach(self.phase1_db, self.phase2_db)
        ref = self.source_ref()
        original = phase2.write_memory(
            self.phase2_db, agent_id='agent-1', memory_id='memory-1',
            memory_kind='episode', content={'text': 'initial'}, source_refs=[ref],
            confidence=.4, salience=.3)
        with closing(weather_store.connect(self.phase2_db)) as db:
            original_payload = db.execute('SELECT payload FROM phase2_memories WHERE memory_id=?', ('memory-1',)).fetchone()[0]
        replacement = phase2.write_memory(
            self.phase2_db, agent_id='agent-1', memory_id='memory-2',
            memory_kind='episode', content={'text': 'corrected'}, source_refs=[ref],
            confidence=.9, salience=.8, supersedes='memory-1')
        self.assertEqual(replacement['record']['supersedes'], 'memory-1')
        self.assertEqual(phase2.memory(self.phase2_db, 'memory-1')['effective_validity'], 'superseded')
        with closing(weather_store.connect(self.phase2_db)) as db:
            self.assertEqual(original_payload, db.execute('SELECT payload FROM phase2_memories WHERE memory_id=?', ('memory-1',)).fetchone()[0])
        phase2.invalidate(self.phase2_db, 'memory-2')
        self.assertEqual(phase2.memory(self.phase2_db, 'memory-2')['effective_validity'], 'invalidated')
        self.assertEqual(len(phase2.memories(self.phase2_db)), 2)
        self.assertEqual(len(phase2.memories(self.phase2_db, active_only=True)), 0)
        self.assertEqual(original['record']['checksum'], phase2.memory(self.phase2_db, 'memory-1')['record']['checksum'])
        self.assertTrue(phase2.replay(self.phase2_db)['phase2_verified'])

    def test_source_references_owner_and_new_destination_boundaries_fail_closed(self):
        phase2.attach(self.phase1_db, self.phase2_db)
        with self.assertRaisesRegex(ValueError, 'source reference'):
            phase2.write_memory(self.phase2_db, agent_id='agent-1', memory_id='bad-ref',
                                memory_kind='episode', content={'text': 'x'}, source_refs=['missing'])
        with self.assertRaisesRegex(ValueError, 'not enrolled'):
            phase2.write_memory(self.phase2_db, agent_id='agent-9', memory_id='bad-owner',
                                memory_kind='episode', content={'text': 'x'}, source_refs=[self.source_ref()])
        with self.assertRaisesRegex(ValueError, 'NEW path'):
            phase2.attach(self.phase1_db, self.phase2_db)

    def test_tampered_memory_and_backup_are_detected(self):
        phase2.attach(self.phase1_db, self.phase2_db)
        phase2.write_memory(self.phase2_db, agent_id='agent-1', memory_id='memory-1',
                            memory_kind='episode', content={'text': 'sealed'},
                            source_refs=[self.source_ref()])
        with closing(weather_store.connect(self.phase2_db, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            payload = json.loads(db.execute('SELECT payload FROM phase2_memories WHERE memory_id=?', ('memory-1',)).fetchone()[0])
            payload['content']['text'] = 'tampered'
            db.execute('UPDATE phase2_memories SET payload=? WHERE memory_id=?',
                       (json.dumps(payload, sort_keys=True, separators=(',', ':')), 'memory-1'))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            phase2.replay(self.phase2_db)
        backup = Path(self.tmp.name) / 'phase2-backup.sqlite'
        # Restore a clean Phase-2 copy for the backup check.
        clean = Path(self.tmp.name) / 'phase2-clean.sqlite'
        phase2.attach(self.phase1_db, clean)
        phase2.write_memory(clean, agent_id='agent-1', memory_id='memory-1',
                            memory_kind='episode', content={'text': 'sealed'}, source_refs=[self.source_ref()])
        phase2.save(clean, backup)
        self.assertTrue(phase2.replay(backup)['phase2_verified'])


if __name__ == '__main__':
    unittest.main()
