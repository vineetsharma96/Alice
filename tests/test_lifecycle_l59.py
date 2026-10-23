import json
import unittest

from underworld import lifecycle_l59 as lifecycle


TRAITS = {
    "body_size_potential": .5,
    "metabolic_efficiency": .5,
    "maturation_tendency": .5,
    "sensory_sensitivity": .5,
}


def person(ident, species="human", age=0, resources=None, knowledge=None):
    return {
        "id": ident,
        "species_id": species,
        "age_steps": age,
        "alive": True,
        "traits": dict(TRAITS),
        "resources": {"food": 4.0} if resources is None else resources,
        "knowledge": ["parent-memory"] if knowledge is None else knowledge,
        "lexicon": ["parent-word"],
        "relationship_ids": ["old-edge"],
    }


def setup_state(capacity=None, hazard=.0):
    state = lifecycle.initial_state("l59-test", seed=7, carrying_capacity=capacity)
    stages = [
        lifecycle.life_stage("dependent", 0, 1, function_scale=.8,
                             care_needs={"food": 1.0}, deprivation_tolerance=0),
        lifecycle.life_stage("adult", 2, None, function_scale=1.0,
                             care_needs={}, mortality_hazard=hazard),
    ]
    lifecycle.register_species(state, "human", stages, max_age_steps=4)
    return state


class LifecycleL59Tests(unittest.TestCase):
    def test_inheritance_controls_bound_variation_and_provenance(self):
        controls = lifecycle.inheritance_controls(max_variation=.02, mutation_rate=.02,
                                                   recombination="mean_only")
        result = lifecycle.inheritance_result("child", ["a", "b"], TRAITS, TRAITS, 3, controls)
        self.assertEqual(result["copied_fields"], [])
        self.assertEqual(result["provenance"], "bounded parent traits; developmental experience only")
        self.assertEqual(result["traits"], TRAITS)
        for mutation in result["mutations"].values():
            self.assertLessEqual(abs(mutation), .02)

    def test_birth_has_no_parental_knowledge_lexicon_or_relationships(self):
        state = setup_state()
        lifecycle.add_individual(state, person("a", resources={"food": 5.0}))
        child = lifecycle.record_birth(state, "child", "human", ["a"], TRAITS,
                                       {key: 0.0 for key in TRAITS}, "birth-1")
        self.assertEqual(child["knowledge"], [])
        self.assertEqual(child["lexicon"], [])
        self.assertEqual(child["relationship_ids"], [])
        self.assertEqual(state["lineages"]["child"]["copied_fields"], [])

    def test_care_accounting_and_deprivation_consequence(self):
        state = setup_state()
        lifecycle.add_individual(state, person("caregiver", resources={"food": 5.0}, age=2))
        lifecycle.add_individual(state, person("dependent", resources={"food": 0.0}))
        proposal = lifecycle.care_proposal(state, "caregiver", "dependent", "food", 1.0, 1, "care-1")
        lifecycle.apply_care_receipt(state, proposal, True)
        applied = lifecycle.apply_care(state, "care-1")
        self.assertTrue(applied["changed"])
        lifecycle.advance_time(state, mortality_rolls={"caregiver": 1.0, "dependent": 1.0})
        self.assertEqual(state["individuals"]["dependent"]["deprivation_steps"], 0)
        self.assertEqual(state["individuals"]["dependent"]["resources"]["food"], 1.0)

        deprived = setup_state()
        lifecycle.add_individual(deprived, person("young", resources={"food": 0.0}))
        lifecycle.advance_time(deprived, mortality_rolls={"young": 1.0})
        self.assertEqual(deprived["individuals"]["young"]["deprivation_steps"], 1)
        self.assertLess(deprived["individuals"]["young"]["function_scale"], .8)

    def test_age_hazard_is_deterministic_and_death_material_is_accounted(self):
        first = setup_state(hazard=.5)
        lifecycle.add_individual(first, person("adult", age=2, resources={"food": 3.0}))
        lifecycle.advance_time(first, mortality_rolls={"adult": .4})
        self.assertFalse(first["individuals"]["adult"]["alive"])
        death = next(iter(first["deaths"].values()))
        self.assertEqual(death["materials"], {"food": 3.0})
        self.assertIn(death["death_id"], first["material_ledger"])
        second = setup_state(hazard=.5)
        lifecycle.add_individual(second, person("adult", age=2, resources={"food": 3.0}))
        lifecycle.advance_time(second, mortality_rolls={"adult": .4})
        self.assertEqual(lifecycle.mortality_hazard(first, "adult"), lifecycle.mortality_hazard(second, "adult"))

    def test_grief_requires_perceived_loss_and_attachment_evidence(self):
        state = setup_state()
        lifecycle.add_individual(state, person("observer", age=2))
        lifecycle.add_individual(state, person("lost", age=2))
        lifecycle.record_evidence(state, lifecycle.loss_evidence("observer", "lost", "loss-1", 1, perceived=True))
        self.assertFalse(lifecycle.trigger_grief(state, "observer", "lost", "loss-1")["triggered"])
        lifecycle.record_evidence(state, lifecycle.attachment_evidence("observer", "lost", "attach-1", 0))
        result = lifecycle.trigger_grief(state, "observer", "lost", "loss-1")
        self.assertTrue(result["triggered"])
        self.assertEqual(result["evidence"], ["attach-1", "loss-1"])
        no_perception = lifecycle.loss_evidence("observer", "lost", "loss-2", 2, perceived=False)
        lifecycle.record_evidence(state, no_perception)
        self.assertFalse(lifecycle.trigger_grief(state, "observer", "lost", "loss-2")["triggered"])

    def test_demographics_capacity_has_no_hidden_culling(self):
        state = setup_state(capacity=1)
        lifecycle.add_individual(state, person("a", age=2))
        lifecycle.add_individual(state, person("b", age=2))
        report = lifecycle.carrying_capacity_report(state)
        self.assertEqual(report["occupancy"], 2)
        self.assertEqual(report["overflow"], 1)
        self.assertFalse(report["hidden_culling"])
        self.assertEqual(report["culling_events"], 0)

    def test_json_restart_replay_and_privacy_rejection(self):
        state = setup_state()
        lifecycle.add_individual(state, person("a", age=2))
        proposal = lifecycle.propose_external_action("care", {"target": "a", "amount": .2})
        self.assertEqual(proposal["execution"], "external")
        self.assertTrue(proposal["proposal_only"])
        with self.assertRaises(ValueError):
            lifecycle.propose_external_action("care", {"operator_override": True})
        restarted = lifecycle.copy_restart(state)
        self.assertEqual(json.loads(lifecycle.dumps(state)), json.loads(lifecycle.dumps(restarted)))
        replay = lifecycle.replay(lifecycle.dumps(restarted))
        self.assertTrue(replay["replay_matches"])
        self.assertEqual(replay["tick"], restarted["clock_step"])


if __name__ == "__main__":
    unittest.main()
