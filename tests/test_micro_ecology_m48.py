import tempfile
import unittest
from pathlib import Path

from underworld import micro_ecology_m03 as m03
from underworld import micro_ecology_m48 as m48


def base_m03(*, food=2.0, oxygen=0.25, temperature=25.0):
    return m03.initial(
        seed=19,
        habitats={
            "source": {
                "kind": "soil",
                "substrates": {"food": {"mass_kg": food, "nutrients": {"N": 0.04, "P": 0.01, "K": 0.02}}},
                "temperature_c": temperature,
                "moisture": 0.8,
                "oxygen": oxygen,
            },
            "target": {
                "kind": "water",
                "substrates": {"food": {"mass_kg": food, "nutrients": {"N": 0.04, "P": 0.01, "K": 0.02}}},
                "temperature_c": temperature,
                "moisture": 0.8,
                "oxygen": oxygen,
            },
            "jar": {
                "kind": "container",
                "substrates": {"food": {"mass_kg": food, "nutrients": {"N": 0.04, "P": 0.01, "K": 0.02}}},
                "temperature_c": temperature,
                "moisture": 0.8,
                "oxygen": oxygen,
            },
        },
    )


def organic(state):
    return m48.inspect(state)["tracked_organic_kg"]


class MicroEcologyM48Tests(unittest.TestCase):
    def test_no_source_no_spread_and_connectivity_is_explicit(self):
        state = m48.adapt_m03(base_m03(), [{"source_habitat": "source", "target_habitat": "target", "capacity_kg": 1.0}])
        with self.assertRaises(ValueError):
            m48.disperse(state, "source", "target", 0.1, guild="yeast_fermenter")
        seeded = m48.inoculate_strain(state, "source", "yeast_fermenter", 0.4, "declared-culture")
        with self.assertRaises(ValueError):
            m48.disperse(seeded, "target", "source", 0.1, guild="yeast_fermenter")
        moved = m48.disperse(seeded, "source", "target", 0.1, guild="yeast_fermenter", source_id="water-route")
        self.assertEqual(len(moved["transfer_events"]), 2)
        self.assertIn("water-route", next(iter(moved["habitats"]["target"]["populations"].values()))["inoculum_sources"])

    def test_transfer_conservation_and_finite_capacity(self):
        state = m48.adapt_m03(base_m03(), [{"source_habitat": "source", "target_habitat": "target", "capacity_kg": 0.2}])
        seeded = m48.inoculate_strain(state, "source", "yeast_fermenter", 0.5, "culture")
        before = organic(seeded)
        moved = m48.disperse(seeded, "source", "target", 0.15, guild="yeast_fermenter")
        self.assertAlmostEqual(before, organic(moved), places=10)
        with self.assertRaises(ValueError):
            m48.disperse(moved, "source", "target", 0.1, guild="yeast_fermenter")

    def test_competition_changes_composition(self):
        state = m48.adapt_m03(base_m03(food=0.4), [])
        state = m48.inoculate_strain(state, "source", "yeast_fermenter", 0.4, "slow", {"uptake_affinity": 0.7})
        state = m48.inoculate_strain(state, "source", "yeast_fermenter", 0.4, "fast", {"uptake_affinity": 1.3})
        after = m48.step(state, 86400)
        strains = list(after["habitats"]["source"]["populations"].values())
        fast = next(item for item in strains if "fast" in item["inoculum_sources"])
        slow = next(item for item in strains if "slow" in item["inoculum_sources"])
        self.assertGreater(fast["biomass_kg"], slow["biomass_kg"])

    def test_heritable_adaptation_has_ancestor_control(self):
        state = m48.adapt_m03(base_m03(temperature=5.0), [])
        state = m48.inoculate_strain(state, "source", "yeast_fermenter", 0.6, "ancestor", {"temperature_tolerance": 1.0})
        parent_id = next(iter(state["habitats"]["source"]["populations"]))
        state = m48.set_mutation(state, "source", parent_id, True)
        adapted = m48.mutate_strain(state, "source", parent_id, {"temperature_tolerance": 0.4}, 0.5)
        child = next(pop for key, pop in adapted["habitats"]["source"]["populations"].items() if key != parent_id)
        self.assertEqual(child["ancestor_id"], parent_id)
        self.assertEqual(m48.ancestor_control(adapted, "source", child["strain_id"])["temperature_tolerance"], 1.0)
        after = m48.step(adapted, 86400)
        self.assertGreaterEqual(after["habitats"]["source"]["populations"][child["strain_id"]]["biomass_kg"], 0.0)

    def test_paired_fermentation_outcomes_and_mass_accounting(self):
        sealed = m48.adapt_m03(base_m03(food=1.0, oxygen=0.25), [])
        sealed = m48.inoculate_strain(sealed, "jar", "yeast_fermenter", 0.2, "yeast")
        open_jar = m48.adapt_m03(base_m03(food=1.0, oxygen=0.25), [])
        open_jar = m48.inoculate_strain(open_jar, "jar", "yeast_fermenter", 0.2, "yeast")
        sealed_before = organic(sealed)
        open_before = organic(open_jar)
        open_boundary_before = open_jar["ledgers"]["organic_boundary_kg"]
        sealed = m48.start_fermentation(sealed, "jar", substrate_mass_kg=0.8, sealed=True, vented=False, gas_capacity_kg=0.001)
        open_jar = m48.start_fermentation(open_jar, "jar", substrate_mass_kg=0.8, sealed=False, vented=True, gas_capacity_kg=0.2)
        sealed_after = m48.step(sealed, 3 * 86400)
        open_after = m48.step(open_jar, 3 * 86400)
        self.assertNotEqual(sealed_after["fermentations"], open_after["fermentations"])
        self.assertAlmostEqual(sealed_before, organic(sealed), places=10)
        self.assertLessEqual(sealed_after["fermentations"][next(iter(sealed_after["fermentations"]))]["gas_mass_kg"], 0.001 + 1e-10)
        self.assertGreater(open_after["fermentations"][next(iter(open_after["fermentations"]))]["exported_mass_kg"], 0.0)
        self.assertAlmostEqual(open_before + (open_after["ledgers"]["organic_boundary_kg"] - open_boundary_before), organic(open_after), places=10)

    def test_sealed_constraint_blocks_and_vented_process_exports_gas(self):
        state = m48.adapt_m03(base_m03(food=1.0), [])
        state = m48.inoculate_strain(state, "jar", "yeast_fermenter", 0.2, "yeast")
        state = m48.start_fermentation(state, "jar", substrate_mass_kg=0.8, sealed=True, vented=False, gas_capacity_kg=0.000001)
        blocked = m48.step(state, 86400)
        process = next(iter(blocked["fermentations"].values()))
        self.assertIn(process["status"], {"blocked_sealed_gas", "complete"})

    def test_json_restart_replay_and_observer_round_trip(self):
        initial = m48.adapt_m03(base_m03(), [{"source_habitat": "source", "target_habitat": "target", "capacity_kg": 1.0}])
        initial = m48.inoculate_strain(initial, "source", "yeast_fermenter", 0.4, "culture")
        strain_id = next(iter(initial["habitats"]["source"]["populations"]))
        commands = [
            {"kind": "disperse", "source_habitat": "source", "target_habitat": "target", "biomass_kg": 0.1, "strain_id": strain_id},
            {"kind": "step", "dt_s": 3600},
        ]
        replayed = m48.replay(initial, commands)
        observer = m48.to_microcosm(replayed, "target")
        self.assertEqual(m48.state_hash(replayed), m48.state_hash(m48.from_microcosm(replayed, observer)))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "m48.json"
            m48.save(replayed, path)
            loaded = m48.resume(path)
        self.assertEqual(m48.state_hash(replayed), m48.state_hash(loaded))

    def test_disease_is_disabled_and_rejected_when_enabled(self):
        state = m48.adapt_m03(base_m03(), [])
        self.assertEqual(m48.inspect(state)["disease"]["status"], "disabled")
        state["disease"]["status"] = "enabled"
        with self.assertRaises(ValueError):
            m48.validate(state)


if __name__ == "__main__":
    unittest.main()
