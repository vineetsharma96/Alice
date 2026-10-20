import copy
import json
import os
from pathlib import Path
import subprocess
import unittest

from underworld.config import load, validate

ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = load(ROOT / "config/baseline.toml")

    def test_reject_invalid_and_unimplemented_configuration(self):
        cases = [("world", "population", 0), ("world", "population", 9),
                 ("world", "population", True), ("world", "dt_s", float("nan")),
                 ("world", "width_m", float("inf")), ("cognition", "provider", "local"),
                 ("cognition", "max_concurrency", 0), ("logging", "event_retention_count", -1)]
        for section, key, value in cases:
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config[section][key] = value
                with self.assertRaises(ValueError):
                    validate(config)

    def test_unknown_schema_and_keys_rejected(self):
        for patch in ({"schema_version": 2}, {"seed": -1}, {"mode": "unknown"}, {"typo": 1}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate(self.config | patch)


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = Path(os.environ["UNDERWORLD_CORE"]).resolve()

    def run_core(self, *args):
        return subprocess.run([str(self.core), *args], capture_output=True, text=True, timeout=15)

    def test_scene_is_seeded_bounded_and_has_stable_unique_ids(self):
        first = self.run_core()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, self.run_core().stdout)
        scene = json.loads(first.stdout)
        entities = scene["entities"]
        self.assertEqual(len(entities), 11)
        self.assertEqual(len({e["entity_id"] for e in entities}), len(entities))
        self.assertEqual(sum(e["kind"] == "inhabitant_seed" for e in entities), 8)
        self.assertEqual(scene["tick"], 0)
        self.assertEqual(scene["cognition"], "not_implemented")
        for entity in entities:
            x, y = entity["position_m"]
            self.assertTrue(0 <= x <= 64 and 0 <= y <= 64)
        changed = json.loads(self.run_core("--seed", "42").stdout)
        self.assertNotEqual(entities[0]["position_m"], changed["entities"][0]["position_m"])
        self.assertEqual([e["entity_id"] for e in entities], [e["entity_id"] for e in changed["entities"]])

    def test_core_rejects_invalid_arguments(self):
        for args in (("--population", "0"), ("--population", "65"), ("--population", "-1"),
                     ("--width-m", "nan"), ("--dt-s", "0"), ("--seed", "-1"),
                     ("--seed", "12x"), ("--unknown", "1"), ("--seed",)):
            with self.subTest(args=args):
                result = self.run_core(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("INVALID_ARGUMENT", result.stderr)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
