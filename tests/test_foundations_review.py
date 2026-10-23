from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from underworld import world_generation_g01 as world, lifecycle_l59 as life
from underworld import lifecycle_l02 as early
from tests.test_lifecycle_l59 import setup_state, person
from tests.test_lifecycle_l02 import species, person as early_person
from underworld import plant_underground_g47 as plants


class FoundationReviewTests(unittest.TestCase):
    def test_density_times_volume_is_kilograms(self):
        self.assertEqual(world._material_mass('stone',1),2600)
        from underworld.plant_underground_g47 import _layer_mass
        self.assertEqual(_layer_mass('stone',1,{'materials':world.MATERIALS}),2600)

    def test_minimum_supported_depth_generates(self):
        state=world.generate(61,world.preset_config(width=4,height=4,layer_depth_m=.5))
        self.assertTrue(world.validate_manifest(state))

    def setup_care(self):
        state=setup_state()
        life.add_individual(state,person('a',age=2));life.add_individual(state,person('b'))
        return state

    def test_negative_care_receipt_is_rejected_without_changing_state(self):
        state=self.setup_care();proposal=life.care_proposal(state,'a','b','food',1,0,'care')
        proposal['amount']=-1;before=deepcopy(state)
        with self.assertRaises(ValueError):life.apply_care_receipt(state,proposal)
        self.assertEqual(before,state)

    def test_conflicting_care_retry_is_rejected(self):
        state=self.setup_care();proposal=life.care_proposal(state,'a','b','food',1,0,'care')
        life.apply_care_receipt(state,proposal);before=deepcopy(state)
        proposal['amount']=2
        with self.assertRaises(ValueError):life.apply_care_receipt(state,proposal)
        self.assertEqual(before,state)

    def test_adult_starts_with_adult_function_scale(self):
        state=self.setup_care()
        self.assertEqual(state['individuals']['a']['function_scale'],1)

    def test_failed_population_add_does_not_leave_invalid_state(self):
        state=early.initial_state();early.register_species(state,species())
        before=deepcopy(state)
        with patch.object(early,'MAX_INDIVIDUALS',0):
            with self.assertRaises(ValueError):early.add_individual(state,early_person('a','male'))
        self.assertEqual(before,state)

    def test_save_cannot_overwrite_when_existence_check_races(self):
        state=world.generate(1,world.preset_config(width=4,height=4))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'world.json';path.write_bytes(b'original evidence')
            with patch.object(Path,'exists',return_value=False):
                with self.assertRaises(FileExistsError):world.save(state,path)
            self.assertEqual(path.read_bytes(),b'original evidence')

    def test_exhausted_soil_cannot_supply_unlimited_plant_nutrients(self):
        manifest=world.generate(61,world.preset_config(width=4,height=4))
        for cell in manifest['cells']:
            for horizon in cell['horizons']:
                horizon['nutrients_available']={k:0 for k in ('N','P','K')}
        manifest['manifest_hash']=world.manifest_hash(manifest)
        state=plants.initialize(manifest,initial_plants=2)
        before={p['plant_id']:p['biomass_kg'] for p in state['plants']}
        result=plants.plant_step(state,days=1)
        for p in result['plants']:
            if p['plant_id'] in before:self.assertEqual(p['biomass_kg'],before[p['plant_id']])

    def test_care_acceptance_retry_cannot_reset_applied_transfers(self):
        state=early.initial_state();early.register_species(state,species())
        early.add_individual(state,early_person('a','male'));early.add_individual(state,early_person('b','female'))
        proposal=early.propose_care(state,'a','b','food',1,0,1,'care')
        early.accept_care(state,proposal,True);early.apply_care(state,'care',0)
        before=deepcopy(state);early.accept_care(state,proposal,True)
        self.assertEqual(before,state)
        self.assertFalse(early.apply_care(state,'care',0)['changed'])

    def test_generation_order_must_be_a_permutation(self):
        with self.assertRaises(ValueError):world.generate_order_invariant(1,world.preset_config(width=4,height=4),orders=[[(0,0)]*16]*2)

    def test_plant_uptake_debits_persistent_pool_with_repeated_source(self):
        manifest=world.generate(61,world.preset_config(width=4,height=4))
        state=plants.initialize(manifest,initial_plants=2)
        def total(s):return sum(h['nutrients_available']['N'] for c in s['source_cells'].values() for h in c['horizons'])
        initial=total(state)
        first=plants.plant_step(state,days=3,source_manifest=manifest)
        second=plants.plant_step(first,days=3,source_manifest=manifest)
        self.assertLess(total(second),total(first));self.assertLess(total(first),initial)
        uptake=sum(e['NPK_units'] for e in second['plant_ledgers']['nutrients'])
        self.assertAlmostEqual(initial-total(second),uptake,places=6)

    def test_zero_time_preserves_physical_plant_state(self):
        manifest=world.generate(61,world.preset_config(width=4,height=4))
        state=plants.initialize(manifest,initial_plants=2)
        result=plants.plant_step(state,days=0)
        self.assertEqual(state['plants'],result['plants'])
        self.assertEqual(state['seed_banks'],result['seed_banks'])
        self.assertEqual(state['plant_ledgers'],result['plant_ledgers'])

    def test_other_sidecar_saves_are_exclusive(self):
        from underworld import micro_ecology_m03 as m03,micro_ecology_m48 as m48
        manifest=world.generate(61,world.preset_config(width=4,height=4))
        microbial=m03.initial()
        for module,state in ((plants,plants.initialize(manifest,initial_plants=0)),(m03,microbial),(m48,m48.adapt_m03(microbial))):
            with self.subTest(module=module.__name__),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'state.json';path.write_bytes(b'original')
                with patch.object(Path,'exists',return_value=False):
                    with self.assertRaises(FileExistsError):module.save(state,path)
                self.assertEqual(path.read_bytes(),b'original')
