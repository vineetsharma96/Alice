import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from underworld.world_generation_g01 import (
    ConflictError,
    deposit,
    excavate,
    extract,
    generate,
    generate_order_invariant,
    inspect,
    manifest_hash,
    preset_config,
    replay,
    resume,
    save,
    soil_step,
    validate_config,
    validate_manifest,
)


class WorldGenerationG01Tests(unittest.TestCase):
    def test_twenty_bounded_seeds_are_structurally_valid(self):
        for seed in range(20):
            world = generate(seed, preset_config("temperate_woodland_meadow", width=8, height=8))
            self.assertTrue(validate_manifest(world))
            self.assertEqual(len(world["cells"]), 64)

    def test_same_seed_hash_and_order_invariance(self):
        config = preset_config("wet_riparian", width=7, height=7)
        self.assertEqual(manifest_hash(generate(42, config)), manifest_hash(generate(42, config)))
        order = [(x, y) for y in range(7) for x in range(7)]
        self.assertTrue(generate_order_invariant(42, config, [order, list(reversed(order))]))

    def test_different_seeds_change_state(self):
        config = preset_config("dry_scrub_rocky", width=8, height=8)
        self.assertNotEqual(manifest_hash(generate(1, config)), manifest_hash(generate(2, config)))

    def test_invalid_config_rejected(self):
        with self.assertRaises(ValueError):
            validate_config(preset_config(width=3))
        with self.assertRaises(ValueError):
            validate_config(preset_config(width=100, height=100))

    def test_extraction_is_finite_and_copy_on_write(self):
        world = generate(9, preset_config(width=8, height=8, diversity=1.0))
        self.assertTrue(world["deposits"])
        deposit_id = world["deposits"][0]["deposit_id"]
        initial = world["deposits"][0]["remaining_ore_kg"]
        changed = extract(world, deposit_id, initial / 2, operation_id="op-1")
        self.assertEqual(world["revision"], 0)
        self.assertLess(changed["deposits"][0]["remaining_ore_kg"], initial)
        self.assertEqual(extract(changed, deposit_id, 1, operation_id="op-1")["revision"], changed["revision"])
        with self.assertRaises(ConflictError):
            extract(changed, deposit_id, 1, expected_revision=0)

    def test_no_inflow_does_not_create_water_and_rain_wets_soil(self):
        world = generate(4, preset_config("dry_scrub_rocky", width=6, height=6))
        before = sum(h["water_m3"] for c in world["cells"] for h in c["horizons"])
        dry = soil_step(world, rainfall_mm=0, temperature_c=20, daylight_fraction=1, dt_days=1)
        after_dry = sum(h["water_m3"] for c in dry["cells"] for h in c["horizons"])
        self.assertLessEqual(after_dry, before + 1e-8)
        wet = soil_step(world, rainfall_mm=40, temperature_c=10, daylight_fraction=0.2, dt_days=1)
        self.assertGreater(sum(h["water_m3"] for c in wet["cells"] for h in c["horizons"]), before)
        self.assertAlmostEqual(wet["ledgers"]["water"][-1]["balance_error"], 0.0, places=7)

    def test_drought_and_waterlogged_conditions(self):
        dry = generate(11, preset_config("dry_scrub_rocky", width=6, height=6))
        dry = soil_step(dry, rainfall_mm=0, temperature_c=35, daylight_fraction=1, dt_days=20)
        wet = generate(11, preset_config("wet_riparian", width=6, height=6))
        wet = soil_step(wet, rainfall_mm=300, temperature_c=8, daylight_fraction=0.1, dt_days=2)
        self.assertGreater(sum(c["plant_condition"]["drought"] for c in dry["cells"]), 0)
        self.assertGreater(sum(c["plant_condition"]["waterlogged"] for c in wet["cells"]), 0)

    def test_excavation_spoil_and_deposit_accounting(self):
        world = generate(3, preset_config(width=6, height=6))
        before = world["cells"][0]["horizons"][0]["volume_m3"]
        dug = excavate(world, 0, 0, "O", min(0.01, before / 2), operation_id="dig-1")
        material = dug["ledgers"]["material_transfers"][-1]["spoil_material"]
        amount = dug["ledgers"]["material_transfers"][-1]["spoil_kg"]
        filled = deposit(dug, 0, 0, material, amount, operation_id="fill-1")
        self.assertGreater(filled["stocks"][material]["deposited_kg"], 0)
        self.assertTrue(validate_manifest(filled))

    def test_json_save_resume_and_replay(self):
        world = generate(8, preset_config(width=5, height=5))
        world2 = soil_step(world, rainfall_mm=10)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "world.json"
            save(world2, path)
            loaded = resume(path)
            self.assertEqual(manifest_hash(world2), manifest_hash(loaded))
            replayed = replay(world, [{"kind": "soil_step", "rainfall_mm": 10}])
            self.assertEqual(manifest_hash(world2), manifest_hash(replayed))
            self.assertEqual(inspect(loaded)["manifest_hash"], manifest_hash(loaded))


if __name__ == "__main__":
    unittest.main()
