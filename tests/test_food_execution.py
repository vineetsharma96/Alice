"""Native-backed regression cases for the authored edible-material executor."""
import copy
import tempfile
from pathlib import Path
import unittest

from ecology_fixtures import world, layout, harness, balances
from underworld import stabilization as stable, storage
from underworld.config import load
from underworld.lab_policy import Driver


def fixture(seed=21, forage=.6):
    return layout(world(seed,forage=forage),positions={
        'agent-1':(3,4.5),'animal-1':(10,3),'animal-2':(10,5),
        'resource-1':(20,3)},fatigue=.95)


def state(o):
    s=dict(agent='agent-1',sequence=0,model=False,model_goals=0,
           fallback_goals=0,navigation={})
    stable._new_goal(s,o,'eat','authored_need_selection')
    return s


def dispatch(h,s,planner=stable):
    request,blocked=planner._next(s,h.observe())
    if request:
        h.act(request['action_type'],request['target_ids'],request['parameters'],request['requested_duration'])
    return request,blocked


class FoodExecutionTests(unittest.TestCase):
    def test_carried_plant_partial_meal_and_mixed_inventory(self):
        for seed in (21,515,626):
            with self.subTest(seed=seed):
                w=fixture(seed);h=harness(w)
                h.act('gather_plant',['forage-1'],{'mass_kg':.06})
                s=state(h.observe());request,blocked=dispatch(h,s)
                self.assertIsNone(blocked);self.assertEqual(request['parameters']['material'],'plant_food')
                self.assertEqual(int(h.observe()['own_state']['body']['food_ingested_ug']),60000000)
                # The next gather requests the remaining goal mass, not another full meal.
                request,blocked=dispatch(h,s)
                self.assertEqual(request['action_type'],'gather_plant')
                self.assertAlmostEqual(request['parameters']['mass_kg'],.14)
                dispatch(h,s)
                self.assertEqual(int(h.observe()['own_state']['body']['food_ingested_ug']),200000000)
                self.assertEqual(set(balances(w).values()),{0})

    def test_gather_sequence_and_observed_depletion(self):
        w=fixture(forage=.2);h=harness(w);s=state(h.observe())
        request,_=dispatch(h,s);self.assertEqual(request['action_type'],'gather_plant')
        request,_=dispatch(h,s);self.assertEqual(request['action_type'],'eat')
        o=h.observe();s=state(o);request,_=stable._next(s,o)
        self.assertNotIn(request['action_type'] if request else None,('eat','gather_plant'))
        self.assertEqual(set(balances(w).values()),{0})

    def test_approach_uses_visible_forage_then_rechecks(self):
        w=layout(fixture(),positions={'agent-1':(2,4.5)})
        h=harness(w);s=state(h.observe())
        request,_=dispatch(h,s);self.assertEqual(request['action_type'],'move')
        request,_=dispatch(h,s);self.assertEqual(request['action_type'],'gather_plant')
        request,_=dispatch(h,s);self.assertEqual(request['action_type'],'eat')
        self.assertEqual(int(h.observe()['own_state']['body']['food_ingested_ug']),200000000)
        self.assertEqual(set(balances(w).values()),{0})

    def test_carried_eggs_are_consumed_as_partial_meal(self):
        w=layout(world(),positions={'agent-1':(3,4.5),'animal-1':(5,5),'animal-2':(4,4.5)},fatigue=.95)
        w.step(150);h=harness(w);h.act('collect_eggs',['animal-2'],{'material':'eggs','mass_kg':.06})
        request,_=dispatch(h,state(h.observe()))
        self.assertEqual(request['parameters']['material'],'eggs')
        self.assertEqual(int(h.observe()['own_state']['body']['food_ingested_ug']),60000000)
        self.assertEqual(set(balances(w).values()),{0})

    def test_expiry_revalidation_and_freshness_aware_selection(self):
        w=fixture(forage=.1);h=harness(w)
        h.act('gather_plant',['forage-1'],{'mass_kg':.1})
        h.step(590)  # One second remains; a two-second meal is infeasible.
        o=h.observe();request,_=stable._next(state(o),o)
        self.assertNotEqual(request['action_type'] if request else None,'eat')
        # Direct native callers still receive the genuine completion-time failure.
        _,receipt=h.submit('eat',params={'material':'plant_food','mass_kg':.1},duration=2)
        self.assertEqual(receipt['status'],'accepted');h.step(10)
        terminal=h.observe()['recent_action_results'][-1]
        self.assertEqual(terminal['status'],'failed')
        self.assertEqual(terminal['error_code'],'INSUFFICIENT_RESOURCE')
        self.assertEqual(set(balances(w).values()),{0})

    def test_perishable_precedes_nonperishable_using_only_own_sight(self):
        w=fixture();h=harness(w);h.act('gather_plant',['forage-1'],{'mass_kg':.1})
        o=copy.deepcopy(h.observe());o['own_state']['inventory_ug']['food']='200000000'
        request,_=stable._next(state(o),o)
        self.assertEqual(request['parameters']['material'],'plant_food')
        # This selection-only observation mock is never restored or committed.

    def test_persistent_interrupted_plant_meal_resume_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'world.sqlite';backup=Path(tmp)/'backup.sqlite'
            cfg=load('config/living-world-d.toml');cfg['world'].update(population=1,dt_s=1)
            cfg['agency'].update(policy='none',food_kg=0,food_regen_kg_s=0,water_regen_kg_s=0)
            storage.create(p,cfg,scripted=False);storage.advance(p,160)
            d=Driver(p,'agent-1');d.navigate((3,4.5));d.act('gather_plant',['forage-1'],{'mass_kg':.2})
            stable.attach(p,['agent-1'])
            # Thirst may precede hunger; run until plant consumption is in flight.
            for _ in range(40):
                stable.step(p)
                pending=stable.status(p)['pending']
                if pending and pending['action_type']=='eat':break
            self.assertEqual(pending['parameters'].get('material'),'plant_food')
            storage.save(p,'mid-plant-meal',backup)
            stable.run(p,8,wall_seconds=60);stable.run(backup,8,wall_seconds=60)
            self.assertEqual(storage.inspect(p)['state_hash'],storage.inspect(backup)['state_hash'])
            self.assertEqual(stable.status(p),stable.status(backup))
            self.assertEqual(storage.mind(p,'agent-1'),storage.mind(backup,'agent-1'))
            self.assertTrue(storage.replay(p)['replay_matches'])
            self.assertTrue(storage.replay(backup)['replay_matches'])
            self.assertGreaterEqual(int(storage.observe(p,['agent-1'])[0]['own_state']['body']['food_ingested_ug']),200000000)
