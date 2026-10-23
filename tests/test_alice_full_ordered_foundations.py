import unittest

from underworld import lifecycle_l02 as l02
from underworld import lifecycle_l59 as l59
from underworld import micro_ecology_m03 as m03
from underworld import micro_ecology_m48 as m48
from underworld import plant_underground_g47 as g47
from underworld import world_generation_g01 as g01


class AliceFullOrderedFoundationsTests(unittest.TestCase):
    def test_g01_g47_m03_m48_l02_l59_ordered_smoke(self):
        manifest = g01.generate(20261023, g01.preset_config(
            "temperate_woodland_meadow", width=6, height=6))
        plants = g47.initialize(manifest, initial_plants=1)
        plants = g47.plant_step(plants, days=3, rainfall_mm=4.0, temperature_c=22.0)
        g47.validate_state(plants)

        cell = manifest["cells"][0]
        microbial = m03.initial(
            seed=20261023,
            habitats={"soil": {
                "kind": "soil",
                "substrates": {"plant_litter": max(1.0, cell["horizons"][0]["organic_matter_kg"])},
                "available_nutrients": {"N": 0.1, "P": 0.02, "K": 0.04},
                "temperature_c": 24.0, "moisture": cell["moisture"], "oxygen": 0.8}},
            inocula=[{"habitat_id": "soil", "guild": "aerobic_decomposer",
                       "biomass_kg": 0.05, "source": "g01"}],
        )
        microbial = m03.step(microbial, 86400)
        overlay = m48.adapt_m03(microbial, routes=[])
        overlay = m48.step(overlay, 86400)
        self.assertEqual(overlay["disease"]["status"], "disabled")
        m48.validate(overlay)

        newborn = l02.life_stage("newborn", 0, 1, False)
        adult = l02.life_stage("adult", 2, None, True)
        male = l02.reproductive_profile("male", "human", "male", ["female"], "adult", 2, {"food": 0.1})
        female = l02.reproductive_profile("female", "human", "female", ["male"], "adult", 2, {"food": 0.1})
        species = l02.species_lifecycle("human", [newborn, adult], [male, female])
        lstate = l02.initial_state("full-order")
        l02.register_species(lstate, species)
        traits = {key: 0.5 for key in l02.TRAIT_RANGES}
        for ident, role, profile in (("a", "male", "male"), ("b", "female", "female")):
            l02.add_individual(lstate, {"id": ident, "species_id": "human", "age_steps": 2,
                                        "stage_id": "adult", "biological_role": role,
                                        "gender_identity": role, "reproductive_profile_id": profile,
                                        "alive": True, "traits": traits, "resources": {"food": 1.0},
                                        "knowledge": [], "lexicon": [], "relationship_ids": []})
        l02.validate_state(lstate)

        l59_state = l59.initial_state("full-order", seed=4)
        controls = l59.inheritance_controls()
        inherited, mutations = l59.inherit_traits(traits, traits, 4, controls)
        self.assertEqual(set(inherited), set(l59.TRAIT_RANGES))
        self.assertEqual(set(mutations), set(l59.TRAIT_RANGES))
        l59.validate_state(l59_state)


if __name__ == "__main__":
    unittest.main()
