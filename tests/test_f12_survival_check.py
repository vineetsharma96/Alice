import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import f12_survival_check


class F12SurvivalCheckTests(unittest.TestCase):
    def test_wall_limit_is_incomplete_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            folder=Path(raw)/'worlds';output=Path(raw)/'result.json'
            with patch.object(f12_survival_check.stabilization,'run',return_value={'status':'wall_limit'}):
                result=f12_survival_check.run_check(output,seconds=2,segment_seconds=1,population=2,folder=folder)
            self.assertFalse(result['duration_completed'])
            self.assertEqual(len(result['integrated']['stages']),1)
            self.assertTrue((folder/'integrated.sqlite').is_file())
            self.assertFalse(result['communication_handshake']['native_delivery_verified'])
            before=output.read_bytes()
            with self.assertRaises(FileExistsError):
                f12_survival_check.run_check(output,seconds=2,segment_seconds=1,population=2)
            self.assertEqual(output.read_bytes(),before)

    def test_connected_survival_smoke_preserves_native_control(self):
        with tempfile.TemporaryDirectory() as raw:
            result = f12_survival_check.run_check(
                output=Path(raw) / "survival.json",
                seconds=1.0,
                segment_seconds=1.0,
                population=2,
                folder=Path(raw)/'worlds',
            )
        self.assertTrue(result["source_unchanged"])
        self.assertTrue(result["native_state_hash_matches_control"])
        self.assertTrue(result["integrated_replay_matches"])
        self.assertEqual(result["actors"], ["agent-1", "agent-2"])
        self.assertTrue(result["communication_handshake"]["feedback_changed"])
        self.assertEqual(result["integrated"]["final"]["f12"]["operation_count"], 4)


if __name__ == "__main__":
    unittest.main()
