from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import continuous_world as runner  # noqa: E402


class ContinuousWorldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'world.sqlite'
        self.path.touch()
        self.stop = threading.Event()
        for name in ('emit', 'validate_model_off', 'storage.inspect', 'Lease'):
            p = patch('continuous_world.' + name)
            mock = p.start()
            self.addCleanup(p.stop)
            if name == 'storage.inspect':
                mock.return_value = {'tick': '60', 'simulated_time_s': 30,
                                     'entities': [{'kind': 'actor', 'alive': True}]}
                self.inspect = mock

    def result(self, status, seconds=30):
        return {'status': status, 'simulated_s': seconds, 'tick': '120',
                'replay': {'replay_matches': True}}

    def test_wall_window_and_segment_end_do_not_end_the_world(self):
        statuses = iter(['wall_limit', 'target_reached', 'stopped'])
        with patch.object(runner.stabilization, 'run', side_effect=lambda *a, **k: self.result(next(statuses))) as advance:
            self.assertEqual(runner.run(self.path, self.stop)['status'], 'stopped')
        self.assertEqual(advance.call_count, 3)
        self.assertTrue(all(call.args[0] == self.path for call in advance.call_args_list))

    def test_quota_is_not_retried(self):
        with patch.object(runner.stabilization, 'run', return_value=self.result('quota_reached')) as advance:
            self.assertEqual(runner.run(self.path, self.stop)['status'], 'quota_reached')
        advance.assert_called_once()

    def test_replay_mismatch_stops(self):
        result = self.result('target_reached')
        result['replay']['replay_matches'] = False
        with patch.object(runner.stabilization, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'replay mismatch'):
                runner.run(self.path, self.stop)

    def test_no_progress_stops_instead_of_busy_retry(self):
        with patch.object(runner.stabilization, 'run', return_value=self.result('wall_limit', 0)):
            with self.assertRaisesRegex(RuntimeError, 'no committed progress'):
                runner.run(self.path, self.stop)

    def test_extinct_population_does_not_advance(self):
        self.inspect.return_value['entities'][0]['alive'] = False
        with patch.object(runner.stabilization, 'run') as advance:
            self.assertEqual(runner.run(self.path, self.stop)['status'], 'population_extinct')
        advance.assert_not_called()

    def test_stop_is_forwarded_to_committed_tick_runner(self):
        def advance(*args, **kwargs):
            self.stop.set()
            self.assertTrue(kwargs['stop_requested']())
            return self.result('stopped', .5)
        with patch.object(runner.stabilization, 'run', side_effect=advance):
            self.assertEqual(runner.run(self.path, self.stop)['status'], 'stopped')

    def test_missing_world_is_never_initialized(self):
        missing = self.path.parent / 'absent.sqlite'
        with self.assertRaisesRegex(ValueError, 'existing saved world'):
            runner.run(missing, self.stop)
        self.assertFalse(missing.exists())

    def test_stop_file_prevents_further_advancement(self):
        stop_file = self.path.parent / 'stop'
        stop_file.touch()
        with patch.object(runner.stabilization, 'run') as advance:
            self.assertEqual(runner.run(self.path, self.stop, stop_file=stop_file)['status'], 'stopped')
        advance.assert_not_called()


if __name__ == '__main__':
    unittest.main()
