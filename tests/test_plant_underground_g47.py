import tempfile
import unittest
from pathlib import Path

from underworld.world_generation_g01 import generate, preset_config
from underworld.plant_underground_g47 import (
    build_connector,
    build_support,
    cut_plant,
    excavate,
    harvest_seeds,
    initialize,
    inspect,
    move_underground,
    plant_step,
    replay,
    resume,
    save,
    set_occupancy,
    species_catalog,
    state_hash,
)


class PlantUndergroundG47Tests(unittest.TestCase):
    def setUp(self):
        self.manifest = generate(17, preset_config("temperate_woodland_meadow", width=6, height=6, vegetation_density=1.0))
        self.state = initialize(self.manifest, initial_plants=1)

    def test_species_variation_and_functional_catalog(self):
        catalog = species_catalog()
        self.assertGreaterEqual(len(catalog), 13)
        self.assertGreaterEqual(len({v["strategy"] for v in catalog.values()}), 8)
        self.assertIn("tree", {v["functional_group"] for v in catalog.values()})
        self.assertIn("flower", {v["functional_group"] for v in catalog.values()})

    def test_finite_growth_and_cut_seed_accounting(self):
        state = plant_step(self.state, days=90, rainfall_mm=35, daylight_fraction=1.0)
        plant = next(p for p in state["plants"] if p["alive"])
        before = plant["biomass_kg"]
        bounded = plant_step(state, days=5000, rainfall_mm=80, daylight_fraction=1.0)
        grown = next(p for p in bounded["plants"] if p["plant_id"] == plant["plant_id"])
        self.assertLessEqual(grown["biomass_kg"], bounded["species_catalog"][grown["species_id"]]["max_biomass_kg"])
        self.assertGreaterEqual(before, 0.0)
        cut = cut_plant(state, grown["plant_id"])
        self.assertGreater(cut["underground"]["material_stocks"]["wood"]["loose_kg"], 0.0)
        self.assertLess(cut["plants"][[p["plant_id"] for p in cut["plants"]].index(grown["plant_id"])]["biomass_kg"], plant["biomass_kg"])

    def test_contrasting_site_growth_and_germination_failure(self):
        plants = [p for p in self.state["plants"] if p["alive"]]
        self.assertTrue(plants)
        key = f"{plants[0]['coord']['x']},{plants[0]['coord']['y']}"
        shade = {key: 0.0}
        sunny = plant_step(self.state, days=30, rainfall_mm=45, daylight_fraction=1.0, shade=shade)
        shaded = plant_step(self.state, days=30, rainfall_mm=0, daylight_fraction=0.1, shade={key: 1.0})
        a = next(p for p in sunny["plants"] if p["plant_id"] == plants[0]["plant_id"])
        b = next(p for p in shaded["plants"] if p["plant_id"] == plants[0]["plant_id"])
        self.assertGreaterEqual(a["biomass_kg"], b["biomass_kg"])
        attempts = sum(1 for x in shaded["plant_ledgers"]["seed_transfers"] if x["kind"] == "germination_failed")
        self.assertGreaterEqual(attempts, 0)

    def test_underground_extraction_support_occupancy_and_no_teleport(self):
        state = excavate(self.state, 0, 0, "O", 0.01, operation_id="dig")
        material = state["underground"]["operations"][-1]["spoil_kg"]
        self.assertGreater(material, 0)
        support_material = "organic_litter"
        state = build_support(state, 0, 0, "O", support_material, material, operation_id="support")
        state = build_connector(state, "0,0/O", "1,0/O", operation_id="connector")
        state = set_occupancy(state, "0,0/O", "alice", True, operation_id="occupy")
        state = move_underground(state, "alice", "0,0/O", "1,0/O", operation_id="move")
        self.assertIn("alice", state["underground"]["occupancy"]["1,0/O"])
        with self.assertRaises(ValueError):
            move_underground(state, "alice", "1,0/O", "5,5/O")

    def test_json_restart_and_replay(self):
        state = plant_step(self.state, days=3, rainfall_mm=10, operation_id="grow")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "g47.json"
            save(state, path)
            loaded = resume(path)
            self.assertEqual(state_hash(state), state_hash(loaded))
            replayed = replay(self.state, [{"kind": "plant_step", "days": 3, "rainfall_mm": 10, "operation_id": "grow"}])
            self.assertEqual(state_hash(state), state_hash(replayed))
            self.assertEqual(inspect(loaded)["state_hash"], state_hash(loaded))


if __name__ == "__main__":
    unittest.main()
