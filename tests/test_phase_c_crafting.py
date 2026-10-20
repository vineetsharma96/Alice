"""Physical recipes, reservation/recovery and rejection regressions."""
import math
import tempfile
from pathlib import Path
import unittest

from underworld.native import load_native
from underworld.config import load
from underworld import storage


from underworld.workshop import AssignedProcedure as Harness

class CraftingTests(unittest.TestCase):
    def test_initial_stone_footprint_is_reserved_across_seeds(self):
        for width,population in [(8,4),(16,4),(16,8)]:
            for seed in range(100):
                with self.subTest(width=width,population=population,seed=seed):
                    world=load_native().World(seed=seed,population=population,width=width,height=width,scripted=False,bodies=True)
                    world.check_invariants()

    def test_harvest_anchor_cannot_teleport_products(self):
        h=Harness();h.move(2,5)
        req,result=h.submit('harvest_branch',['tree-1'],{'mass_kg':.5,'x_m':6,'y_m':4.5})
        self.assertEqual(result['error_code'],'INVALID_ARGUMENT')
        self.assertEqual(len([e for e in h.snapshot()['entities'] if e['kind'] in ('wood','fiber')]),0)

    def test_complete_physical_chain_and_usable_storage(self):
        h=Harness();site=h.site();h.act('work_construction',[site],duration=8)
        self.assertEqual(h.entity('storage_box')['entity_id'],site)
        self.assertEqual(h.entity('tool')['durability'],6)
        self.assertEqual(next(e for e in h.snapshot()['entities'] if e['entity_id']=='tree-2')['stage'],'stump')
        before=h.observe()['own_state']['inventory_ug']['wood_offcut']
        h.act('store_item',[site],{'material':'wood_offcut','mass_kg':.2})
        self.assertEqual(next(e for e in h.snapshot()['entities'] if e['entity_id']==site)['inventory_ug']['wood_offcut'],'200000000')
        h.act('take_item',[site],{'material':'wood_offcut','mass_kg':.2})
        self.assertEqual(h.observe()['own_state']['inventory_ug']['wood_offcut'],before)
        h.world.check_invariants()

    def test_cancelled_craft_consumes_nothing_and_restart_is_exact(self):
        h=Harness();h.bootstrap();before=h.observe()['own_state']['inventory_ug']
        h.submit('craft',params={'recipe_id':'crude_axe'},duration=4);h.step(5)
        state=h.world.checkpoint();copy=load_native().World.restore(state)
        h.world.step(15);copy.step(15);self.assertEqual(h.world.checkpoint(),copy.checkpoint())
        h.world=load_native().World.restore(state)
        h.act('cancel_action');self.assertEqual(h.observe()['own_state']['inventory_ug'],before)
        self.assertFalse(any(e['kind']=='tool' for e in h.snapshot()['entities']))

    def test_partial_construction_resume_and_cancel_return_material(self):
        h=Harness();site=h.site();h.submit('work_construction',[site],duration=8);h.step(10)
        partial=h.entity('construction')['work_s'];self.assertGreater(partial,0)
        state=h.world.checkpoint();copy=load_native().World.restore(state)
        h.world.step(30);copy.step(30);self.assertEqual(h.world.checkpoint(),copy.checkpoint())
        h.world=load_native().World.restore(state);h.act('cancel_action')
        self.assertEqual(h.entity('construction')['work_s'],partial)
        h.act('cancel_construction',[site]);self.assertEqual(h.observe()['own_state']['inventory_ug']['plank'],'800000000')
        h.world.check_invariants()

    def test_rejections_preserve_resources(self):
        h=Harness()
        self.assertEqual(h.submit('craft',params={'recipe_id':'invented'})[1]['error_code'],'UNKNOWN_RECIPE')
        self.assertEqual(h.submit('craft',params={'recipe_id':'planks'},duration=3)[1]['error_code'],'MISSING_TOOL')
        self.assertEqual(h.submit('craft',params={'recipe_id':'crude_axe'},duration=4)[1]['error_code'],'INSUFFICIENT_RESOURCE')
        h.bootstrap();before=h.observe()['own_state']['inventory_ug']
        self.assertEqual(h.submit('craft',params={'recipe_id':'crude_axe'},duration=1)[1]['error_code'],'INSUFFICIENT_WORK')
        self.assertEqual(h.observe()['own_state']['inventory_ug'],before)
        with self.assertRaises(ValueError):h.submit('craft',params={'recipe_id':'crude_axe','invented_output':'gold'})
        h.world.check_invariants()

    def test_blocked_and_remote_site_do_not_consume(self):
        h=Harness();h.plank_stock();before=h.observe()['own_state']['inventory_ug']
        self.assertEqual(h.submit('begin_construction',params={'recipe_id':'storage_box','x_m':7.2,'y_m':3.4})[1]['error_code'],'NO_PLACEMENT')
        self.assertEqual(h.submit('begin_construction',params={'recipe_id':'storage_box','x_m':1,'y_m':1})[1]['error_code'],'OUT_OF_REACH')
        self.assertEqual(h.observe()['own_state']['inventory_ug'],before)
        h.world.check_invariants()

    def test_gate_and_fence_have_real_collision(self):
        h=Harness();site=h.site('gate');h.act('work_construction',[site],duration=4)
        req,_=h.submit('move',params={'x_m':6.7,'y_m':5.2},duration=3);h.step(15)
        result=next(r for r in h.observe()['recent_action_results'] if r['request_id']==req['request_id'])
        self.assertEqual(result['error_code'],'COLLISION')
        h.act('toggle_gate',[site]);h.move(6.7,4.3)
        self.assertEqual(h.submit('toggle_gate',[site])[1]['error_code'],'NO_PLACEMENT')
        h.move(6.7,5.2);h.act('toggle_gate',[site]);self.assertEqual(next(e for e in h.snapshot()['entities'] if e['entity_id']==site)['radius_m'],.5)
        h.world.check_invariants()

    def test_recipe_registry_not_in_agent_perception(self):
        n=load_native();self.assertEqual(len(n.recipe_registry('operator')),6)
        for recipe in n.recipe_registry('operator'):
            if recipe['kind']=='carried':self.assertEqual(sum(recipe['inputs_ug'].values()),sum(recipe['outputs_ug'].values()))
        with self.assertRaises(ValueError):n.recipe_registry('agent-1')
        self.assertNotIn('recipes',Harness().observe())
        h=Harness(world=n.World(population=1,width=64,height=64,scripted=False,bodies=True))
        self.assertTrue(any(e['kind']=='tree' for e in h.snapshot()['entities']))
        with self.assertRaises(StopIteration):h.entity('tree')

    def test_growth_cap_and_more_than_three_inventory_species_restart(self):
        w=load_native().World(population=1,width=8,height=8,dt=1,scripted=False,tree_growth_kg_s=.007)
        w.step(858);self.assertEqual(next(e for e in w.snapshot()['entities'] if e['entity_id']=='tree-1')['biomass_ug'],'8000000000')
        h=Harness();h.bootstrap();h.move(3,2.7);h.act('gather',['resource-1'],{'mass_kg':.1});h.act('gather',['resource-2'],{'mass_kg':.1})
        self.assertGreater(len(h.observe()['own_state']['inventory_ug']),3)
        self.assertEqual(load_native().World.restore(h.world.checkpoint()).checkpoint(),h.world.checkpoint())

    def test_harvest_entity_quota_fails_before_creating_products(self):
        h=Harness();h.move(2,5);snapshot=h.snapshot();solids=[(e['position_m'],e['radius_m']) for e in snapshot['entities'] if e['radius_m']>0]
        # A declared crowded test fixture uses zero-mass stone records: no
        # inventory or boundary source is changed to exercise the 200-ID quota.
        additions=[]
        needed=199-len(snapshot['entities'])
        for x in range(22):
            for y in range(22):
                p=(.2+.35*x,.2+.35*y)
                if len(additions)==needed:break
                if any(math.dist(p,q)<r+.15-1e-12 for q,r in solids):continue
                solids.append((p,.15))
                additions.append(f'"quota-{len(additions)}" "stone" {p[0]} {p[1]} 0.15 0 0 0.35 0.4 0.2 1 1 0 0 "none" 1 0 "" "" 0 0 0 0')
        self.assertEqual(len(additions),needed)
        lines=h.world.checkpoint().splitlines();end=4+int(lines[3]);lines[3]='199';lines[end:end]=additions
        h.world=load_native().World.restore('\n'.join(lines)+'\n')
        before=next(e for e in h.snapshot()['entities'] if e['entity_id']=='tree-1')['mass_ug']
        req,r=h.submit('harvest_branch',['tree-1'],{'mass_kg':.5});self.assertEqual(r['status'],'accepted');h.step(5)
        result=next(r for r in h.observe()['recent_action_results'] if r['request_id']==req['request_id'])
        self.assertEqual(result['error_code'],'ENTITY_LIMIT');self.assertEqual(len(h.snapshot()['entities']),199)
        self.assertEqual(next(e for e in h.snapshot()['entities'] if e['entity_id']=='tree-1')['mass_ug'],before)
        h.world.check_invariants()

    def test_full_inventory_includes_owned_tool_mass(self):
        h=Harness();h.axe();h.move(3,2.7)
        self.assertEqual(h.submit('gather',['resource-1'],{'mass_kg':1.4})[1]['error_code'],'CAPACITY_EXCEEDED')
        h.act('gather',['resource-1'],{'mass_kg':1.3});h.world.check_invariants()

    def test_competing_builders_and_output_placement_revalidate(self):
        h=Harness();site=h.site()
        # A fresh test-only native fixture adds a second worker at a valid,
        # nonoverlapping location, before any work begins. No product is granted.
        text=h.world.checkpoint();lines=text.splitlines();i=next(i for i,x in enumerate(lines) if x.startswith('"agent-1" "actor"'))
        import shlex
        fields=shlex.split(lines[i]);tail=7+2*int(fields[6])
        actor='"agent-2" "actor" 7.5 5.1 0.25 0 0 '+' '.join(fields[tail:tail+7])+ ' "none" 1 0 "" "" 0 0 0 0'
        lines[3]=str(int(lines[3])+1);lines.insert(i+1,actor)
        h.world=load_native().World.restore('\n'.join(lines)+'\n')
        h.submit('work_construction',[site],duration=8)
        self.assertEqual(h.submit('work_construction',[site],duration=8,agent='agent-2')[1]['error_code'],'TARGET_BUSY')
        h.step(40);h.world.check_invariants()

    def test_breakage_returns_scrap_and_broken_tool_rejects(self):
        h=Harness();site=h.site();h.act('work_construction',[site],duration=8)
        h.act('store_item',[site],{'material':'wood_offcut','mass_kg':.2})
        # Test-only fault fixture: a worn axe with one remaining use. Composition
        # and source ledger stay intact. The actual break happens natively.
        state=h.world.checkpoint();old='"crude_axe" "agent-1" 0 6 '
        self.assertIn(old,state);h.world=load_native().World.restore(state.replace(old,'"crude_axe" "agent-1" 0 1 ',1))
        wood=next(e for e in h.snapshot()['entities'] if e['kind']=='wood' and int(e['mass_ug'])>=1000000000)
        h.act('collect_wood',[wood['entity_id']],{'material':'wood','mass_kg':1})
        tool=h.entity('tool')['entity_id'];h.act('craft',params={'recipe_id':'planks','tool_id':tool},duration=3)
        self.assertEqual(h.entity('spent_tool')['mass_ug'],'0')
        self.assertEqual(h.observe()['own_state']['inventory_ug']['stone'],'200000000')
        self.assertEqual(h.submit('craft',params={'recipe_id':'planks','tool_id':tool},duration=3)[1]['error_code'],'MISSING_TOOL')
        h.world.check_invariants()

    def test_fence_is_solid_and_trough_conserves_real_water(self):
        h=Harness();site=h.site('fence');h.act('work_construction',[site],duration=4)
        self.assertEqual(h.entity('fence')['radius_m'],.5)
        req,_=h.submit('move',params={'x_m':6.7,'y_m':5.2},duration=3);h.step(15)
        self.assertEqual(next(r for r in h.observe()['recent_action_results'] if r['request_id']==req['request_id'])['error_code'],'COLLISION')
        h=Harness();site=h.site('trough');h.act('work_construction',[site],duration=8)
        for p in [(6.35,3.6),(5.5,3.7),(4.8,2.7),(3,2.7)]:h.move(*p)
        h.act('gather',['resource-2'],{'mass_kg':.5})
        for p in [(4.8,2.7),(5.5,3.7),(6.35,3.6),(7.2,3.4)]:h.move(*p)
        initial=h.snapshot()['material_totals_ug']['water']
        h.act('fill_trough',[site],{'material':'water','mass_kg':.5})
        self.assertEqual(next(e for e in h.snapshot()['entities'] if e['entity_id']==site)['inventory_ug']['water'],'500000000')
        self.assertEqual(h.snapshot()['material_totals_ug']['water'],initial)
        h.world.check_invariants()

    def test_competing_site_creation_fails_without_consuming_second_inputs(self):
        h=Harness();h.plank_stock()
        # Two legitimate separate four-second reservations for the same space.
        # Each actor starts with 0.4 kg split from existing, accounted planks.
        lines=h.world.checkpoint().splitlines();i=next(i for i,x in enumerate(lines) if x.startswith('"agent-1" "actor"'))
        self.assertIn('"plank" 800000000',lines[i]);lines[i]=lines[i].replace('"plank" 800000000','"plank" 400000000')
        lines[3]=str(int(lines[3])+1)
        lines.insert(i+1,'"agent-2" "actor" 7.5 5.1 0.25 0 1 "plank" 400000000 0.35 0.4 0.2 1 1 0 0 "none" 1 0 "" "" 0 0 0 0')
        h.world=load_native().World.restore('\n'.join(lines)+'\n')
        h.submit('begin_construction',params={'recipe_id':'fence','x_m':6.7,'y_m':4.3})
        second,_=h.submit('begin_construction',params={'recipe_id':'fence','x_m':6.7,'y_m':4.3},agent='agent-2')
        h.step(5)
        result=next(r for r in h.observe('agent-2')['recent_action_results'] if r['request_id']==second['request_id'])
        self.assertIn(result['error_code'],('NO_PLACEMENT','TARGET_UNAVAILABLE'))
        self.assertEqual(h.observe('agent-2')['own_state']['inventory_ug']['plank'],'400000000')
        self.assertEqual(sum(e['kind']=='construction' for e in h.snapshot()['entities']),1)
        h.world.check_invariants()


class DurableCraftingTests(unittest.TestCase):
    def test_observer_cannot_run_a_competing_stabilized_time_controller(self):
        from underworld import stabilization
        from underworld.observer import Controller
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'world.sqlite';c=load('config/living-world.toml');storage.create(db,c,scripted=False)
            stabilization.attach(db,call_limit=0)
            with self.assertRaisesRegex(ValueError,'read-only'):Controller(db)
            before=storage.inspect(db)['state_hash'];controller=Controller(db,readonly=True)
            self.assertEqual(controller.state()['controller']['active'],'stabilization')
            from underworld.viewer import packet
            projection=packet(controller)['controller']
            self.assertEqual(projection['active'],'stabilization')
            self.assertEqual(projection['stabilization']['call_limit'],0)
            with self.assertRaises(ValueError):controller.control({'command':'step'})
            self.assertEqual(storage.inspect(db)['state_hash'],before)
            from contextlib import closing
            with closing(storage._connect(db)) as connection:
                connection.execute("UPDATE stabilization_events SET payload='{}' WHERE id=1")
            with self.assertRaisesRegex(ValueError,'event chain'):packet(controller)

    def test_partial_site_database_backup_and_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'world.sqlite';backup=Path(folder)/'backup.sqlite'
            c=load('config/living-world.toml');c['world'].update(population=1,width_m=8.,height_m=8.);c['agency']['tree_growth_kg_s']=0
            storage.create(db,c,scripted=False);h=Harness(db=db);site=h.site();h.submit('work_construction',[site],duration=8);h.step(10)
            storage.save(db,'mid-construction',backup)
            h.step(35);other=Harness(db=backup);other.step(35)
            self.assertEqual(h.snapshot()['state_hash'],other.snapshot()['state_hash'])
            self.assertTrue(storage.replay(db)['replay_matches']);self.assertTrue(storage.replay(backup)['replay_matches'])
            self.assertEqual(h.entity('storage_box')['entity_id'],site)


if __name__=='__main__':unittest.main()
