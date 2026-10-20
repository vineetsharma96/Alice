from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from underworld import storage,stabilization as stable
from underworld.lab_policy import Driver
from scripts.stabilization_common import create,clone


class StabilizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.path=self.root/'world.sqlite'
        create(self.path,population=1,age=160)

    def tearDown(self):self.tmp.cleanup()

    def own(self,path=None):return storage.observe(path or self.path,['agent-1'])[0]['own_state']

    def attach(self,**kw):return stable.attach(self.path,['agent-1'],**kw)

    def test_handoff_preserves_native_state_and_memories(self):
        before=storage.inspect(self.path);mind=storage.mind(self.path,'agent-1')
        self.attach();after=storage.inspect(self.path)
        self.assertEqual(before['state_hash'],after['state_hash']);self.assertEqual(mind,storage.mind(self.path,'agent-1'))
        with self.assertRaisesRegex(ValueError,'already attached'):self.attach()
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_approach_gather_consume_revalidated(self):
        Driver(self.path,'agent-1').navigate((6,2));before=storage.inspect(self.path)['material_totals_ug']
        self.attach();stable.run(self.path,40,agents=['agent-1'])
        body=self.own()['body']
        self.assertGreaterEqual(int(body['food_ingested_ug']),200000000)
        self.assertGreaterEqual(int(body['water_ingested_ug']),300000000)
        self.assertEqual(before,storage.inspect(self.path)['material_totals_ug'])
        with closing(sqlite3.connect(self.path)) as db:
            kinds=[json.loads(r[0])['action_type'] for r in db.execute("SELECT request FROM decisions WHERE request LIKE '%stable-%'")]
            bad=[json.loads(r[0]) for r in db.execute('SELECT result FROM decisions') if json.loads(r[0])['status']=='rejected']
        self.assertIn('move',kinds);self.assertIn('gather',kinds);self.assertIn('eat',kinds);self.assertFalse(bad)

    def test_carried_food_is_consumed_without_another_food_gather(self):
        Driver(self.path,'agent-1').act('gather',['resource-1'],{'mass_kg':.2})
        self.attach();stable.run(self.path,15,agents=['agent-1'])
        self.assertGreaterEqual(int(self.own()['body']['food_ingested_ug']),200000000)
        self.assertEqual(stable.status(self.path)['calls'],0)

    def test_depleted_target_rechecked_before_request(self):
        path=self.root/'competition.sqlite';create(path,population=2,age=160)
        driver=Driver(path,'agent-1');driver.act('gather',['resource-2'],{'mass_kg':.3});driver.act('drink',parameters={'mass_kg':.3})
        driver.navigate((6,2));stable.attach(path,['agent-1']);stable.step(path,['agent-1'])
        self.assertEqual(stable.status(path)['goal']['phase'],'approach')
        Driver(path,'agent-2').act('gather',['resource-1'],{'mass_kg':.8})
        stable.run(path,20,agents=['agent-1'])
        self.assertEqual(int(self.own(path)['body']['food_ingested_ug']),0)
        with closing(sqlite3.connect(path)) as db:
            requests=[json.loads(r[0]) for r in db.execute('SELECT request FROM decisions')]
        self.assertFalse(any(r['request_id'].startswith('stable-') and r['action_type'] in ('eat','gather') for r in requests))

    def test_scarcity_never_submits_empty_eat_and_retry_is_bounded(self):
        other=self.root/'scarce.sqlite';create(other,population=1,age=160,food=0)
        stable.attach(other,['agent-1']);stable.run(other,45,agents=['agent-1'])
        with closing(sqlite3.connect(other)) as db:
            reqs=[json.loads(r[0]) for r in db.execute('SELECT request FROM decisions')]
        self.assertFalse(any(r['action_type']=='eat' for r in reqs));self.assertLess(len(reqs),25)
        self.assertTrue(self.own(other)['alive'])

    def test_after_commit_crash_reconciles_without_double_consumption(self):
        Driver(self.path,'agent-1').act('gather',['resource-1'],{'mass_kg':.2})
        self.attach()
        def fail(stage):
            if stage=='after_native_commit':raise RuntimeError('simulated interruption')
        with self.assertRaises(RuntimeError):stable.step(self.path,['agent-1'],fault=fail)
        stable.run(self.path,15,agents=['agent-1'])
        self.assertEqual(int(self.own()['body']['food_ingested_ug']),200000000)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_unsubmitted_reservation_does_not_duplicate_action(self):
        self.attach()
        def fail(stage):raise RuntimeError('before native submit')
        with self.assertRaises(RuntimeError):stable.step(self.path,['agent-1'],fault=fail)
        self.assertEqual(storage.inspect(self.path)['recorded_decisions'],0)
        stable.run(self.path,15,agents=['agent-1'])
        self.assertEqual(int(self.own()['body']['water_ingested_ug']),300000000)

    def test_save_resume_controller_native_memory_and_scheduler_match(self):
        driver=Driver(self.path,'agent-1');driver.act('gather',['resource-2'],{'mass_kg':.3});driver.act('drink',parameters={'mass_kg':.3})
        driver.act('gather',['resource-1'],{'mass_kg':.2})
        self.attach();stable.run(self.path,1,agents=['agent-1']);self.assertTrue(self.own()['busy'])
        backup=self.root/'saved.sqlite';storage.save(self.path,'mid_action',backup)
        self.assertEqual(stable.status(self.path),stable.status(backup))
        stable.run(self.path,20,agents=['agent-1']);stable.run(backup,20,agents=['agent-1'])
        self.assertEqual(storage.inspect(self.path)['state_hash'],storage.inspect(backup)['state_hash'])
        self.assertEqual(storage.mind(self.path,'agent-1'),storage.mind(backup,'agent-1'))
        self.assertEqual(stable.status(self.path),stable.status(backup))

    def test_model_eat_becomes_authored_prerequisite_sequence(self):
        self.attach(model=True,call_limit=1)
        raw=json.dumps(dict(intent='eat',target='',text='',interpretation='Need food',evidence=[]))
        with patch('underworld.cognition.bounded_call',return_value=(raw,{'model':'unit-fixture'},.01)):
            stable.run(self.path,15,agents=['agent-1'])
        state=stable.status(self.path)
        self.assertEqual(state['model_goals'],1);self.assertGreaterEqual(state['fallback_goals'],1)
        self.assertGreaterEqual(int(self.own()['body']['food_ingested_ug']),200000000)
        self.assertGreater(state['authored_steps'],0)

    def test_provider_failure_is_explicit_fallback_and_consumes_budget(self):
        self.attach(model=True,call_limit=1)
        with patch('underworld.cognition.bounded_call',side_effect=TimeoutError('unit timeout')) as mocked:
            stable.run(self.path,15,agents=['agent-1'])
        self.assertEqual(mocked.call_count,1);self.assertEqual(stable.status(self.path)['calls'],1)
        self.assertGreater(stable.status(self.path)['fallback_goals'],0)

    def test_private_input_and_control_corruption(self):
        self.attach()
        o=storage.observe(self.path,['agent-1'])[0]
        c=stable._context(o,storage.mind(self.path,'agent-1'))
        self.assertNotIn('entities',c);self.assertNotIn('state_hash',c)
        self.assertEqual(c['perception']['own']['inventory_ug'],o['own_state']['inventory_ug'])
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE stabilization_agents SET payload='{}'");db.commit()
        with self.assertRaisesRegex(ValueError,'checksum'):stable.status(self.path)

    def test_learning_module_is_not_a_dependency(self):
        self.assertNotIn('learning',Path(stable.__file__).read_text().split('from . import')[1].split('\n')[0])

    def test_scripted_model_handoff_cannot_dispatch_old_scheduler(self):
        from underworld.config import load
        cfg=load(Path(__file__).resolve().parents[1]/'config/survival.toml')
        cfg['cognition']['provider']='llama.cpp';cfg['world'].update(population=1,population_limit=1)
        other=self.root/'scripted.sqlite';storage.create(other,cfg,scripted=True)
        stable.attach(other,['agent-1'])
        with patch('underworld.storage.think',side_effect=AssertionError('old scheduler must be disabled')):
            stable.run(other,1,agents=['agent-1'])
        self.assertEqual(storage.inspect(other)['cognition_calls'],0)

    def test_external_rest_interrupts_goal_without_losing_gathered_inventory(self):
        self.attach();stable.step(self.path,['agent-1'])
        Driver(self.path,'agent-1').act('rest',seconds=10)
        stable.run(self.path,15,agents=['agent-1'])
        self.assertEqual(int(self.own()['body']['water_ingested_ug']),300000000)
        self.assertEqual(int(self.own()['body']['food_ingested_ug']),200000000)

    def test_external_consumption_is_not_credited_to_executor(self):
        self.attach();stable.step(self.path,['agent-1'])
        Driver(self.path,'agent-1').act('drink',parameters={'mass_kg':.3})
        stable.step(self.path,['agent-1'])
        with closing(sqlite3.connect(self.path)) as db:
            events=[json.loads(r[0]) for r in db.execute('SELECT payload FROM stabilization_events')]
        self.assertTrue(any(e['kind']=='goal_completed' and e['data']['reason']=='external_native_consumption_not_executor_credit' for e in events))

    def test_blocked_first_approach_uses_another_perceived_direction(self):
        path=self.root/'crowded-water.sqlite';create(path,population=2,age=160,food=0)
        Driver(path,'agent-2').navigate((2,1));Driver(path,'agent-1').navigate((1,1))
        stable.attach(path,['agent-1']);stable.run(path,25,agents=['agent-1'])
        self.assertGreaterEqual(int(self.own(path)['body']['water_ingested_ug']),300000000)
        with closing(sqlite3.connect(path)) as db:
            rejections=[json.loads(r[0]) for r in db.execute('SELECT result FROM decisions') if json.loads(r[0])['status']=='rejected']
        self.assertFalse(rejections)

    def test_model_unavailable_food_cannot_hide_feasible_crowded_water(self):
        path=self.root/'model-crowded-water.sqlite';create(path,population=2,age=160,food=0)
        Driver(path,'agent-2').navigate((2,1));stable.attach(path,['agent-1'],model=True,call_limit=1)
        raw=json.dumps(dict(intent='eat',target='',text='',interpretation='Need food',evidence=[]))
        with patch('underworld.cognition.bounded_call',return_value=(raw,{'model':'unit-fixture'},.01)):
            stable.run(path,35,agents=['agent-1'])
        self.assertGreaterEqual(int(self.own(path)['body']['water_ingested_ug']),300000000)
        self.assertEqual(int(self.own(path)['body']['food_ingested_ug']),0)


if __name__=='__main__':unittest.main()
