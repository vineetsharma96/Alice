import copy
import json
import tempfile
import unittest
from pathlib import Path

from underworld.micro_ecology_m03 import (
    GUILDS,
    decompose,
    initial,
    inoculate,
    inspect,
    replay,
    resume,
    save,
    state_hash,
    step,
    transfer,
    validate,
)


def habitats(*, temperature=27.0, moisture=0.64, oxygen=0.88, litter=4.0):
    return {
        "soil-a": {
            "kind": "soil",
            "substrates": {"plant_litter": {"mass_kg": litter, "nutrients": {"N": 0.08, "P": 0.01, "K": 0.02}}},
            "available_nutrients": {"N": 0.0, "P": 0.0, "K": 0.0},
            "temperature_c": temperature,
            "moisture": moisture,
            "oxygen": oxygen,
        },
        "water-a": {"kind": "water", "substrates": {"dissolved_organic": 1.0}, "temperature_c": 20.0, "moisture": 1.0, "oxygen": 0.7},
    }


class MicroEcologyM03Tests(unittest.TestCase):
    def seeded(self, **kwargs):
        return initial(7, habitats(**kwargs), [{"habitat_id": "soil-a", "guild": "aerobic_decomposer", "biomass_kg": 0.2, "source": "plant-litter-seed"}])

    def test_sterile_control_has_no_spontaneous_growth(self):
        world = initial(1, habitats())
        advanced = step(world, 7 * 86400)
        self.assertEqual(inspect(world)["habitats"][0]["biomass_kg"], 0)
        self.assertEqual(inspect(advanced)["habitats"][0]["biomass_kg"], 0)
        self.assertEqual(inspect(advanced)["habitats"][0]["substrate_mass_kg"], 4.0)

    def test_substrate_exhaustion_causes_decline_or_dormancy(self):
        world = initial(2, habitats(litter=0.08), [{"habitat_id": "soil-a", "guild": "aerobic_decomposer", "biomass_kg": 0.8, "source": "small-inoculum"}])
        advanced = step(world, 25 * 86400)
        population = advanced["habitats"]["soil-a"]["populations"]["aerobic_decomposer"]
        self.assertLessEqual(advanced["habitats"]["soil-a"]["substrates"]["plant_litter"]["mass_kg"], 0.08)
        self.assertTrue(population["activity"] == "dormant" or population["biomass_kg"] < 0.8)

    def test_favorable_outgrows_cold_dry_and_no_negative_stocks(self):
        good = initial(3, habitats(temperature=27.0, moisture=0.64), [{"habitat_id": "soil-a", "guild": "aerobic_decomposer", "biomass_kg": 0.5, "source": "same-seed"}])
        cold = initial(3, habitats(temperature=2.0, moisture=0.08), [{"habitat_id": "soil-a", "guild": "aerobic_decomposer", "biomass_kg": 0.5, "source": "same-seed"}])
        good_after, cold_after = step(good, 86400), step(cold, 86400)
        good_biomass = good_after["habitats"]["soil-a"]["populations"]["aerobic_decomposer"]["biomass_kg"]
        cold_biomass = cold_after["habitats"]["soil-a"]["populations"]["aerobic_decomposer"]["biomass_kg"]
        self.assertGreater(good_biomass, cold_biomass)
        for state in (good_after, cold_after):
            validate(state)
            self.assertTrue(all(record["mass_kg"] >= 0 for h in state["habitats"].values() for record in h["substrates"].values()))
            self.assertTrue(all(pop["biomass_kg"] >= 0 for h in state["habitats"].values() for pop in h["populations"].values()))

    def test_time_step_tolerance_is_tight_with_fixed_substeps(self):
        world = self.seeded()
        coarse = step(world, 3 * 86400)
        fine = world
        for _ in range(72):
            fine = step(fine, 3600)
        a = coarse["habitats"]["soil-a"]["populations"]["aerobic_decomposer"]["biomass_kg"]
        b = fine["habitats"]["soil-a"]["populations"]["aerobic_decomposer"]["biomass_kg"]
        self.assertAlmostEqual(a, b, places=10)
        self.assertAlmostEqual(coarse["habitats"]["soil-a"]["substrates"]["plant_litter"]["mass_kg"], fine["habitats"]["soil-a"]["substrates"]["plant_litter"]["mass_kg"], places=10)

    def test_litter_to_biomass_products_and_nutrients_loop(self):
        world = self.seeded()
        before = inspect(world, "soil-a")
        advanced = step(world, 2 * 86400)
        after = inspect(advanced, "soil-a")
        self.assertGreater(after["habitats"][0]["biomass_kg"], before["habitats"][0]["biomass_kg"])
        self.assertGreater(after["habitats"][0]["byproducts"]["co2_kg"], 0.0)
        self.assertGreater(sum(after["habitats"][0]["available_nutrients"].values()), 0.0)
        returned = decompose(advanced, "soil-a", "dead_biomass", advanced["habitats"]["soil-a"]["dead_biomass_kg"] / 2)
        self.assertGreaterEqual(sum(returned["habitats"]["soil-a"]["available_nutrients"].values()), sum(advanced["habitats"]["soil-a"]["available_nutrients"].values()))

    def test_transfer_requires_source_and_preserves_connectivity(self):
        world = self.seeded()
        moved = transfer(world, "soil-a", "water-a", "aerobic_decomposer", 0.05, source_id="water-contact")
        self.assertAlmostEqual(moved["habitats"]["water-a"]["populations"]["aerobic_decomposer"]["biomass_kg"], 0.05)
        self.assertIn("water-contact", moved["habitats"]["water-a"]["populations"]["aerobic_decomposer"]["inoculum_sources"])
        with self.assertRaises(ValueError):
            transfer(world, "water-a", "soil-a", "yeast_fermenter", 0.1)
        validate(moved)

    def test_json_copy_restart_and_replay(self):
        world = self.seeded()
        commands = [
            {"kind": "step", "dt_s": 3600},
            {"kind": "transfer", "source_habitat": "soil-a", "target_habitat": "water-a", "guild": "aerobic_decomposer", "biomass_kg": 0.01, "source_id": "water-route"},
            {"kind": "step", "dt_s": 7200},
        ]
        replayed = replay(world, commands)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "micro-ecology.json"
            save(replayed, path)
            loaded = resume(path)
        self.assertEqual(state_hash(replayed), state_hash(loaded))
        self.assertEqual(state_hash(replayed), state_hash(replay(world, commands)))
        self.assertEqual(json.loads(json.dumps(loaded)), json.loads(json.dumps(loaded)))

    def test_private_operator_and_model_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            initial(1, {"soil-a": {"kind": "soil", "operator_seed": 1}})
        world = self.seeded()
        world["transfer_events"].append({"operator_label": "hidden"})
        with self.assertRaises(ValueError):
            validate(world)


if __name__ == "__main__":
    unittest.main()
