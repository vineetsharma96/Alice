"""D's predeclared physical gates, independent of model or learned policies."""
from contextlib import closing
import math
import tempfile
from pathlib import Path
import unittest

from underworld import storage, stabilization
from underworld.native import load_native
from underworld.config import load
from ecology_fixtures import world,layout,pen,harness,balances


def entity(w,id):return next(e for e in w.snapshot()['entities'] if e['entity_id']==id)


class EcologyTests(unittest.TestCase):
    def test_population_sources_and_agent_privacy(self):
        w=world();s=w.snapshot();self.assertEqual(len(s['ecology']['animals']),2)
        self.assertEqual(s['initial_mass_ug']['food'],int(18.5e9))
        self.assertEqual(set(balances(w).values()),{0})
        obs=w.observe_batch(['agent-1'])[0]
        self.assertNotIn('ecology',obs)
        for e in obs['visible_entities']:
            if e['kind']=='animal':
                self.assertNotIn('inventory_ug',e);self.assertNotIn('familiarity',e);self.assertNotIn('body',e)
        with self.assertRaises(ValueError):w.configure_ecology()

    def test_starvation_caretaking_and_heldout_ledgers(self):
        for seed in (21,44,73):
            poor=pen(seed,False);good=pen(seed,True)
            # Remove outside water from the poor animals' reach through a real closed pen.
            for w in (poor,good):w.step(1500);self.assertEqual(set(balances(w).values()),{0})
            poor_health=sum(entity(poor,f'animal-{i}')['condition']=='good' for i in (1,2))
            good_health=sum(entity(good,f'animal-{i}')['condition']=='good' for i in (1,2))
            self.assertGreater(good_health,poor_health)
            self.assertGreater(int(good.snapshot()['ecology']['eggs_produced_ug']),0)
            self.assertGreater(sum(int(a['water_metabolized_ug']) for a in good.snapshot()['ecology']['animals'].values()),0)

    def test_animals_leave_water_and_actually_eat_accessible_forage(self):
        w=world(width=16);events=w.step(1500)
        for id in ('animal-1','animal-2'):
            self.assertTrue(any(e['type']=='animal_foraged' and e['agent_id']==id for e in events))
            self.assertTrue(any(e['type']=='animal_drank' and e['agent_id']==id for e in events))
            self.assertTrue(entity(w,id)['alive'])
        self.assertLess(int(entity(w,'forage-1')['mass_ug']),2000000000)
        self.assertEqual(set(balances(w).values()),{0})

    def test_closed_pen_and_native_open_gate_exit(self):
        w=pen();w.step(600)
        for i in (1,2):
            x,y=entity(w,f'animal-{i}')['position_m'];self.assertTrue(5<x<8.6 and 5<y<8.6)
        h=harness(w);h.act('toggle_gate',['fixture-1']);h.move(7.4,4)
        escaped=False
        for _ in range(600):
            h.step(1)
            if entity(w,'animal-1')['position_m'][1]<4.8:escaped=True;break
        self.assertTrue(escaped,'opened physical gate must permit actual native movement')
        self.assertEqual(set(balances(w).values()),{0})

    def test_feed_history_lure_rejections_and_resume(self):
        w=layout(world(forage=0,water=0),positions={'agent-1':(3,3.8),'animal-1':(4,3.8),'animal-2':(5,5)},fatigue=1)
        h=harness(w)
        self.assertEqual(h.submit('guide_or_lure',['animal-1'])[1]['error_code'],'UNFAMILIAR')
        h.move(2.5,3);h.act('gather',['resource-1'],{'mass_kg':.1});h.move(3,3.8)
        h.act('observe_animal',['animal-1'],duration=.2)
        h.act('offer_feed',['animal-1'],{'material':'food','mass_kg':.01})
        h.act('offer_feed',['animal-1'],{'material':'food','mass_kg':.01})
        self.assertEqual(w.snapshot()['ecology']['animals']['animal-1']['familiarity']['agent-1'],1)
        h.step(50);h.act('offer_feed',['animal-1'],{'material':'food','mass_kg':.01})
        h.act('guide_or_lure',['animal-1'])
        state=w.checkpoint();copy=load_native().World.restore(state);w.step(15);copy.step(15)
        self.assertEqual(copy.checkpoint(),w.checkpoint());self.assertEqual(set(balances(w).values()),{0})
        h.step(35);h.act('offer_feed',['animal-1'],{'material':'food','mass_kg':.01})
        self.assertEqual(entity(w,'animal-1')['stage'],'domestic')
        self.assertEqual(w.snapshot()['ecology']['animals']['animal-1']['familiarity']['agent-1'],3)

    def test_plant_depletion_and_freshness(self):
        w=layout(world(forage=.1),positions={'agent-1':(3,4.5),'animal-1':(5,5),'animal-2':(5,6)},fatigue=.95)
        h=harness(w);h.act('gather_plant',['forage-1'],{'mass_kg':.1})
        self.assertEqual(h.submit('gather_plant',['forage-1'],{'mass_kg':.01})[1]['error_code'],'INSUFFICIENT_RESOURCE')
        h.act('eat',params={'material':'plant_food','mass_kg':.02},duration=2)
        h.step(600)
        self.assertEqual(int(h.observe()['own_state']['inventory_ug']['plant_food']),0)
        self.assertEqual(h.submit('eat',params={'material':'plant_food','mass_kg':.01},duration=2)[1]['error_code'],'INSUFFICIENT_RESOURCE')
        self.assertEqual(set(balances(w).values()),{0})

    def test_storage_slows_spoilage_but_never_refreshes(self):
        w=layout(world(forage=.2),positions={'agent-1':(3,4.5),'animal-1':(10,3),'animal-2':(10,5)},fatigue=.95,structures=[('storage_box',3,5.5)])
        h=harness(w);h.act('gather_plant',['forage-1'],{'mass_kg':.1});h.step(100)
        before=h.observe()['own_state']['freshness_s']['plant_food']
        h.act('store_item',['fixture-0'],{'material':'plant_food','mass_kg':.1});h.step(100)
        h.act('take_item',['fixture-0'],{'material':'plant_food','mass_kg':.05})
        after=h.observe()['own_state']['freshness_s']['plant_food'];self.assertLess(after,before);self.assertGreater(after,before-15)
        h.act('gather_plant',['forage-1'],{'mass_kg':.1})
        self.assertLess(h.observe()['own_state']['freshness_s']['plant_food'],after)
        h.step(1200);self.assertEqual(entity(w,'fixture-0')['inventory_ug']['plant_food'],'0');self.assertEqual(set(balances(w).values()),{0})

    def test_eggs_are_reserve_funded_collection_is_idempotent_and_edible(self):
        w=layout(world(),positions={'agent-1':(3,4.5),'animal-1':(5,5),'animal-2':(4,4.5)},fatigue=.95)
        w.step(150)
        e=w.snapshot()['ecology'];self.assertEqual(int(e['egg_input_ug'])*3,int(e['eggs_produced_ug'])*4)
        self.assertGreater(int(e['eggs_produced_ug']),0)
        h=harness(w);request,result=h.submit('collect_eggs',['animal-2'],{'material':'eggs','mass_kg':.06})
        self.assertEqual(result['status'],'accepted');h.step(5)
        receipt=w.submit(request,'agent-1');self.assertEqual(receipt['status'],'completed')
        self.assertEqual(h.observe()['own_state']['inventory_ug']['eggs'],'60000000')
        self.assertEqual(h.submit('collect_eggs',['animal-2'],{'material':'eggs','mass_kg':.06})[1]['error_code'],'INSUFFICIENT_RESOURCE')
        h.act('eat',params={'material':'eggs','mass_kg':.06},duration=2)
        self.assertEqual(h.observe()['own_state']['body']['food_ingested_ug'],'60000000');self.assertEqual(set(balances(w).values()),{0})

    def test_trough_fill_and_real_animal_consumption(self):
        w=layout(world(forage=0),positions={'agent-1':(3,3),'animal-1':(4.2,3),'animal-2':(6,5),'resource-2':(3,2),'resource-4':(7,2)},fatigue=.95,structures=[('trough',4.5,2.3)])
        h=harness(w);h.act('gather',['resource-2'],{'mass_kg':.2});h.move(3.3,2.8)
        h.act('fill_trough',['fixture-0'],{'material':'water','mass_kg':.2})
        self.assertEqual(entity(w,'fixture-0')['inventory_ug']['water'],'200000000')
        # Continued native movement must consume the accessible trough rather than mint water.
        h.move(2,3);w.step(500)
        self.assertLess(int(entity(w,'fixture-0')['inventory_ug']['water']),200000000)
        self.assertEqual(set(balances(w).values()),{0})

    def test_inflight_care_depletion_cancellation_and_restart(self):
        w=layout(world(forage=.1),positions={'agent-1':(3,4.5),'animal-1':(5,5),'animal-2':(5,6)},fatigue=.95)
        h=harness(w);req,_=h.submit('gather_plant',['forage-1'],{'mass_kg':.1},duration=4);h.step(5)
        state=w.checkpoint();copy=load_native().World.restore(state);w.step(15);copy.step(15)
        self.assertEqual(copy.checkpoint(),w.checkpoint())
        h.world=load_native().World.restore(state);h.act('cancel_action');h.step(30)
        self.assertNotIn('plant_food',h.observe()['own_state']['inventory_ug'])
        self.assertEqual(set(balances(h.world).values()),{0})

    def test_regeneration_is_capped_explicit_and_restartable(self):
        w=world(forage=1.99,rate=.01);w.step(20);self.assertLessEqual(int(entity(w,'forage-1')['mass_ug']),2000000000)
        self.assertGreater(w.snapshot()['boundary_sources_ug']['food'],0)
        state=w.checkpoint();copy=load_native().World.restore(state);w.step(200);copy.step(200)
        self.assertEqual(w.checkpoint(),copy.checkpoint());self.assertEqual(set(balances(w).values()),{0})

    def test_competing_gather_revalidates_stock_without_overdraft(self):
        w=layout(world(forage=.1,population=2),positions={'agent-1':(3,4.5),'agent-2':(3.7,3.5),'animal-1':(10,3),'animal-2':(10,5)})
        h=harness(w)
        for id in ('agent-1','agent-2'):
            self.assertEqual(h.submit('gather_plant',['forage-1'],{'mass_kg':.1},agent=id)[1]['status'],'accepted')
        w.step(5)
        results=[w.observe_batch([id])[0]['recent_action_results'][-1] for id in ('agent-1','agent-2')]
        self.assertEqual([r['status'] for r in results],['completed','failed'])
        self.assertEqual(results[1]['error_code'],'INSUFFICIENT_RESOURCE');self.assertEqual(entity(w,'forage-1')['mass_ug'],'0')
        self.assertEqual(set(balances(w).values()),{0})

    def test_competing_collection_does_not_duplicate_eggs(self):
        w=layout(world(population=2),positions={'agent-1':(3,4.5),'agent-2':(4,3.5),'animal-1':(10,3),'animal-2':(4,4.5)},fatigue=1)
        w.step(150);h=harness(w)
        for id in ('agent-1','agent-2'):
            self.assertEqual(h.submit('collect_eggs',['animal-2'],{'material':'eggs','mass_kg':.06},agent=id)[1]['status'],'accepted')
        w.step(5)
        results=[w.observe_batch([id])[0]['recent_action_results'][-1] for id in ('agent-1','agent-2')]
        self.assertEqual([r['status'] for r in results],['completed','failed'])
        self.assertEqual(results[1]['error_code'],'INSUFFICIENT_RESOURCE')
        self.assertEqual(sum(int(entity(w,id)['inventory_ug'].get('eggs',0)) for id in ('agent-1','agent-2')),60000000)
        self.assertEqual(set(balances(w).values()),{0})

    def test_native_ecology_initial_placement_small_layouts(self):
        for size in (8,16):
            for seed in range(20):
                w=world(seed=seed,width=size,population=4);w.check_invariants()
                p=entity(w,'forage-1')['position_m']
                for e in w.snapshot()['entities']:
                    if e['radius_m']>0:self.assertGreaterEqual(math.dist(p,e['position_m']),e['radius_m']-1e-10)

    def test_bad_material_hidden_and_capacity_rejections(self):
        w=world();h=harness(w)
        self.assertEqual(h.submit('offer_feed',['animal-1'],{'material':'stone','mass_kg':.01})[1]['error_code'],'OUT_OF_REACH')
        self.assertEqual(h.submit('gather_plant',['tree-1'],{'mass_kg':.01})[1]['error_code'],'TARGET_UNAVAILABLE')
        with self.assertRaises(ValueError):h.submit('observe_animal',['animal-1'],{'grant_ownership':True})
        self.assertEqual(h.submit('eat',params={'material':'water','mass_kg':.01},duration=2)[1]['error_code'],'INVALID_ARGUMENT')
        self.assertEqual(set(balances(w).values()),{0})

    def test_strict_config_database_backup_replay_and_no_reinitialization(self):
        config=load('config/living-world-d.toml');config['world']['population']=1
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'run.sqlite';backup=Path(tmp)/'saved.sqlite';storage.create(path,config,scripted=False)
            stabilization.attach(path,call_limit=0,model=False)
            stabilization.run(path,seconds=2,wall_seconds=60)
            storage.save(path,"mid-ecology",backup);stabilization.run(path,seconds=2,wall_seconds=60);stabilization.run(backup,seconds=2,wall_seconds=60)
            self.assertEqual(storage.inspect(path),storage.inspect(backup))
            self.assertTrue(storage.replay(path)['replay_matches'])
            with self.assertRaises(FileExistsError):storage.create(path,config)
            with closing(storage._connect(path,readonly=True)) as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],10)


if __name__=='__main__':unittest.main()
