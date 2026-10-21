from pathlib import Path
from contextlib import closing
import tempfile
import unittest

from underworld import weather_store as store


class WeatherStoreTests(unittest.TestCase):
    def test_cohort_cursor_and_private_state_resume_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'world.sqlite';copy=Path(directory)/'copy.sqlite'
            store.initialize(path,population=4)
            for _ in range(3):store.commit(path,dict(kind='cohort'))
            store.save(path,copy)
            for p in (path,copy):store.commit(p,dict(kind='cohort'))
            self.assertEqual(store.inspect(path),store.inspect(copy))
            self.assertEqual(store.inspect(path)['policy']['_scheduler']['cursor'],4)
            self.assertTrue(store.replay(path)['replay_matches'])

    def test_atomic_journal_inspection_backup_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'weather.sqlite'
            initial = store.initialize(path, population=1)
            self.assertEqual(initial, store.inspect(path))
            with self.assertRaises(ValueError):store.initialize(path)
            store.commit(path, dict(kind='step', ticks=375))
            before = store.inspect(path)
            store.observe(path, 'agent-1')
            self.assertEqual(before, store.inspect(path))
            copy = Path(directory) / 'copy.sqlite'
            self.assertEqual(store.save(path, copy), before)
            for target in (path, copy):store.commit(target, dict(kind='step', ticks=177))
            self.assertEqual(store.inspect(path), store.inspect(copy))
            self.assertTrue(store.replay(path)['replay_matches'])
            with self.assertRaises(ValueError):store.save(path, copy)

    def test_invalid_operation_rolls_back_and_old_schema_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'weather.sqlite'
            store.initialize(path, population=1)
            before = store.inspect(path)
            for ticks in (-1, 10001, True, 2.5):
                with self.assertRaises(ValueError):store.commit(path, dict(kind='step', ticks=ticks))
            self.assertEqual(before, store.inspect(path))
            with closing(store.connect(path, False)) as db:db.execute("UPDATE weather_meta SET value='UW9' WHERE key='format'")
            with self.assertRaises(ValueError):store.inspect(path)


if __name__ == '__main__':unittest.main()
