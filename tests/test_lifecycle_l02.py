import json
import unittest

from underworld import lifecycle_l02 as lifecycle


def species(species_id="humanlike", incompatible=False):
    stages = [
        lifecycle.life_stage("newborn", 0, 1, False),
        lifecycle.life_stage("adult", 2, None, True, {"movement": "full", "care": "possible"}),
    ]
    if incompatible:
        male_roles, female_roles = ["male"], ["female"]
    else:
        male_roles, female_roles = ["female"], ["male"]
    profiles = [
        lifecycle.reproductive_profile("male-profile", species_id, "male", male_roles, "adult", 2, {"food": 1.0}, 1.0),
        lifecycle.reproductive_profile("female-profile", species_id, "female", female_roles, "adult", 2, {"food": 1.0}, 1.0),
    ]
    return lifecycle.species_lifecycle(species_id, stages, profiles)


def person(ident, role, age=2, resources=None, species_id="humanlike", profile_id=None):
    return {
        "id": ident,
        "species_id": species_id,
        "age_steps": age,
        "stage_id": "adult" if age >= 2 else "newborn",
        "biological_role": role,
        "gender_identity": "unknown",
        "reproductive_profile_id": profile_id or ("male-profile" if role == "male" else "female-profile"),
        "alive": True,
        "traits": {
            "body_size_potential": .5,
            "metabolic_efficiency": .5,
            "maturation_tendency": .5,
            "sensory_sensitivity": .5,
        },
        "resources": resources if resources is not None else {"food": 10.0},
        "knowledge": ["parent-secret"],
        "lexicon": ["private-token"],
        "relationship_ids": ["old-edge"],
    }


def current_context(a, b, step=0, roll=0.0):
    return {
        "step": step,
        "proximity": .5,
        "current_intentions": {a: True, b: True},
        "conditions": {a: {"ready": True, "available": True}, b: {"ready": True, "available": True}},
        "roll": roll,
    }


class LifecycleL02Tests(unittest.TestCase):
    def setUp(self):
        self.state = lifecycle.initial_state("run-1")
        lifecycle.register_species(self.state, species())
        lifecycle.add_individual(self.state, person("a", "male"))
        lifecycle.add_individual(self.state, person("b", "female"))

    def test_invalid_immature_and_incompatible_pairs_are_rejected(self):
        immature = lifecycle.initial_state("run-immature")
        lifecycle.register_species(immature, species())
        lifecycle.add_individual(immature, person("young", "male", age=0, profile_id="male-profile"))
        lifecycle.add_individual(immature, person("adult", "female"))
        with self.assertRaisesRegex(ValueError, "mature"):
            lifecycle.propose_conception(immature, "young", "adult", current_context("young", "adult"))

        incompatible = lifecycle.initial_state("run-incompatible")
        lifecycle.register_species(incompatible, species(incompatible=True))
        lifecycle.add_individual(incompatible, person("x", "male"))
        lifecycle.add_individual(incompatible, person("y", "female"))
        with self.assertRaisesRegex(ValueError, "incompatible"):
            lifecycle.propose_conception(incompatible, "x", "y", current_context("x", "y"))

    def test_directional_affection_and_declined_invitation_are_not_reciprocal(self):
        lifecycle.record_relationship(self.state, lifecycle.relationship_evidence("a", "b", "aff-1", "affection", 1, .8, 0.0))
        rel = self.state["relationships"]["a->b"]
        self.assertGreater(rel["affection"], 0)
        self.assertNotIn("b->a", self.state["relationships"])

        invitation = lifecycle.propose_partnership(self.state, "a", "b", "invite-1", 2)
        lifecycle.decide_partnership(self.state, invitation["invitation_id"], "a", False)
        self.assertEqual(self.state["partnership_invitations"]["invite-1"]["status"], "declined")
        self.assertNotIn("invite-1", self.state["partnerships"])

    def test_mutual_partnership_requires_two_accepted_decisions(self):
        invitation = lifecycle.propose_partnership(self.state, "a", "b", "invite-2", 2)
        lifecycle.decide_partnership(self.state, invitation["invitation_id"], "a", True)
        self.assertNotIn("invite-2", self.state["partnerships"])
        lifecycle.decide_partnership(self.state, invitation["invitation_id"], "b", True)
        partnership = self.state["partnerships"]["invite-2"]
        self.assertEqual(partnership["accepted_decisions"], {"a": True, "b": True})

    def test_conception_prerequisites_and_one_per_step(self):
        with self.assertRaisesRegex(ValueError, "proximity"):
            lifecycle.propose_conception(self.state, "a", "b", {**current_context("a", "b"), "proximity": 2.0})
        proposal = lifecycle.propose_conception(self.state, "a", "b", current_context("a", "b", step=3))
        pregnancy = lifecycle.apply_conception(self.state, proposal, "conceive-1")
        self.assertEqual(pregnancy["status"], "active")
        with self.assertRaisesRegex(ValueError, "active pregnancy"):
            lifecycle.propose_conception(self.state, "a", "b", current_context("a", "b", step=3))

    def test_gestation_cost_and_birth_are_exactly_once(self):
        proposal = lifecycle.propose_conception(self.state, "a", "b", current_context("a", "b"))
        lifecycle.apply_conception(self.state, proposal, "conceive-2")
        events = lifecycle.advance_time(self.state, 1)
        self.assertFalse(any(event["kind"] == "birth" for event in events))
        self.assertEqual(self.state["individuals"]["b"]["resources"]["food"], 9.0)
        events = lifecycle.advance_time(self.state, 1)
        births = [event for event in events if event["kind"] == "birth"]
        self.assertEqual(len(births), 1)
        child_id = births[0]["child_id"]
        self.assertEqual(len(self.state["birth_events"]), 1)
        self.assertEqual(len(self.state["individuals"]), 3)
        self.assertEqual(lifecycle.advance_time(self.state, 1), [])
        self.assertEqual(len(self.state["individuals"]), 3)
        self.assertEqual(self.state["individuals"][child_id]["knowledge"], [])
        self.assertEqual(self.state["individuals"][child_id]["lexicon"], [])
        self.assertEqual(self.state["individuals"][child_id]["relationship_ids"], [])

    def test_inheritance_is_bounded_and_varies_without_knowledge_copy(self):
        first, mutations = lifecycle.inherit_traits(self.state["individuals"]["a"]["traits"], self.state["individuals"]["b"]["traits"], 1)
        second, _ = lifecycle.inherit_traits(self.state["individuals"]["a"]["traits"], self.state["individuals"]["b"]["traits"], 2)
        self.assertNotEqual(first, second)
        for traits in (first, second):
            for value in traits.values():
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)
        self.assertEqual(set(mutations), set(lifecycle.TRAIT_RANGES))

    def test_care_accounting_and_json_copy_restart(self):
        proposal = lifecycle.propose_care(self.state, "a", "b", "food", 1.5, 0, 2, "care-1")
        lifecycle.accept_care(self.state, proposal, True)
        self.assertTrue(lifecycle.apply_care(self.state, "care-1", 0)["changed"])
        self.assertFalse(lifecycle.apply_care(self.state, "care-1", 0)["changed"])
        self.assertEqual(self.state["individuals"]["a"]["resources"]["food"], 8.5)
        restarted = lifecycle.copy_restart(self.state)
        self.assertEqual(json.loads(lifecycle.dumps(self.state)), json.loads(lifecycle.dumps(restarted)))
        self.assertEqual(restarted["care_commitments"]["care-1"]["applied_steps"], [0])

    def test_private_operator_model_fields_and_invalid_identity_are_rejected(self):
        invalid = person("bad", "male")
        invalid["operator_override"] = True
        with self.assertRaisesRegex(ValueError, "private, operator, and model"):
            lifecycle.add_individual(self.state, invalid)
        invalid_identity = person("bad-identity", "male")
        invalid_identity["gender_identity"] = "imaginary"
        with self.assertRaisesRegex(ValueError, "gender identity"):
            lifecycle.add_individual(self.state, invalid_identity)


if __name__ == "__main__":
    unittest.main()
