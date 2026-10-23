import unittest

from underworld import lifecycle_l02 as lifecycle
from underworld import micro_ecology_m03 as ecology
from underworld import world_generation_g01 as world


class AliceFoundationIntegrationTests(unittest.TestCase):
    def test_ordered_g01_to_l02_to_m03_foundations(self):
        manifest = world.generate(20261023, world.preset_config(
            "temperate_woodland_meadow", width=6, height=6))
        world.validate_manifest(manifest)
        self.assertEqual(manifest["contract_version"], "alice.world.g01/v1")
        cell = manifest["cells"][0]
        litter = max(1.0, cell["horizons"][0]["organic_matter_kg"])

        microbial = ecology.initial(
            seed=20261023,
            habitats={"soil-from-g01": {
                "kind": "soil",
                "substrates": {"plant_litter": litter},
                "available_nutrients": {"N": 0.1, "P": 0.02, "K": 0.04},
                "temperature_c": 24.0, "moisture": cell["moisture"], "oxygen": 0.8,
            }},
            inocula=[{"habitat_id": "soil-from-g01",
                       "guild": "aerobic_decomposer", "biomass_kg": 0.05,
                       "source": "g01-seeded-litter"}],
        )
        microbial = ecology.step(microbial, 86400)
        self.assertGreaterEqual(microbial["habitats"]["soil-from-g01"]["populations"]["aerobic_decomposer"]["biomass_kg"], 0.0)
        ecology.validate(microbial)

        newborn = lifecycle.life_stage("newborn", 0, 1, False)
        adult = lifecycle.life_stage("adult", 2, None, True)
        male = lifecycle.reproductive_profile(
            "human-male", "human", "male", ["female"], "adult", 2,
            {"food": 0.1}, conception_probability=1.0)
        female = lifecycle.reproductive_profile(
            "human-female", "human", "female", ["male"], "adult", 2,
            {"food": 0.1}, conception_probability=1.0)
        species = lifecycle.species_lifecycle("human", [newborn, adult], [male, female])
        state = lifecycle.initial_state("ordered-foundation-run")
        lifecycle.register_species(state, species)
        traits = {key: 0.5 for key in lifecycle.TRAIT_RANGES}
        lifecycle.add_individual(state, {
            "id": "alice", "species_id": "human", "age_steps": 2,
            "stage_id": "adult", "biological_role": "male", "gender_identity": "male",
            "reproductive_profile_id": "human-male", "alive": True, "traits": traits,
            "resources": {"food": 1.0}, "knowledge": [], "lexicon": [],
            "relationship_ids": [],
        })
        lifecycle.add_individual(state, {
            "id": "bob", "species_id": "human", "age_steps": 2,
            "stage_id": "adult", "biological_role": "female", "gender_identity": "female",
            "reproductive_profile_id": "human-female", "alive": True, "traits": traits,
            "resources": {"food": 1.0}, "knowledge": [], "lexicon": [],
            "relationship_ids": [],
        })
        lifecycle.validate_state(state)
        self.assertEqual(set(state["individuals"]), {"alice", "bob"})


if __name__ == "__main__":
    unittest.main()
