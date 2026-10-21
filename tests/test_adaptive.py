from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import adaptive as ad, composition as comp, developmental as dev, storage
from scripts.adaptive_study import online, relief, train_locations, prepare, cooperation


class AdaptiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'world.sqlite'
        ad.initialize(self.path,53)

    def test_existing_vocabulary_and_native_body_survive_explicit_attachment(self):
        p=self.path.parent/'existing.sqlite';comp.initialize(p,53)
        comp.encode(p,'agent-1','resource-1',True)
        old=comp.audit(p);head=storage.inspect(p)['state_hash']
        ad.attach(p,['agent-1'])
        new=ad.audit(p)
        self.assertEqual(new['h5_memory_hashes'],old['h5_memory_hashes'])
        self.assertEqual(storage.inspect(p)['state_hash'],head)
        self.assertEqual(new['people']['agent-2'],old['people']['agent-2'])
        with self.assertRaisesRegex(ValueError,'already attached'):ad.attach(p,['agent-1'])
        with self.assertRaisesRegex(ValueError,'private adaptive'):ad.private(p,'agent-1','agent-2')

    def test_online_range_failure_does_not_erase_food_affordance(self):
        p=self.path.parent/'online.sqlite';r=online(p,53,'adaptive')
        self.assertEqual(r['successes'],6)
        self.assertEqual(r['final']['native_rejections'],['OUT_OF_REACH'])
        self.assertTrue(r['final']['replay']['replay_matches'])

    def test_busy_failure_is_distinct_from_reach_and_quality(self):
        o=dev.own_observation(self.path,'agent-1')
        request=dict(schema_version=1,run_id=o['run_id'],request_id='occupy',agent_id='agent-1',
            observation_version=o['observation_version'],action_type='rest',target_ids=[],parameters={},requested_duration=10)
        storage.advance(self.path,1,[(int(o['tick']),request)])
        e=dev.execute(self.path,'agent-1','gather',['resource-1'],{'mass_kg':.001},update_memory=False)
        ad.learn_outcome(self.path,'agent-1',e['request']['request_id'])
        h=ad.private(self.path,'agent-1','agent-1')
        self.assertNotEqual(e['receipt']['status'],'completed')
        self.assertEqual(h['quality'],{});self.assertEqual(h['ranges'],[])

    def test_native_primitive_retries_do_not_repeat_physics(self):
        def fail(stage):
            if stage=='after_native_commit':raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):ad.perform(self.path,'agent-1','once','gather',['resource-1'],{'mass_kg':.001},fault=fail)
        first=ad.perform(self.path,'agent-1','once','gather',['resource-1'],{'mass_kg':.001})
        head=storage.inspect(self.path)['state_hash']
        self.assertEqual(ad.perform(self.path,'agent-1','once','gather',['resource-1'],{'mass_kg':.001}),first)
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)
        with self.assertRaisesRegex(ValueError,'conflicting logical'):ad.perform(self.path,'agent-1','once','rest')

    def test_interrupted_gather_plan_resumes_then_consumes_once_after_epoch(self):
        relief(self.path,'agent-1')
        dev.execute(self.path,'agent-1','rest',duration=60,update_memory=False)
        dev.execute(self.path,'agent-1','rest',duration=60,update_memory=False)
        def fail(stage):
            if stage=='after_plan_native':raise RuntimeError(stage)
        for _ in range(12):
            try:ad.step(self.path,'agent-1',fault=fail)
            except RuntimeError:pass
            p=ad.private(self.path,'agent-1','agent-1')['pending']
            if p and p['role']=='gather':break
            ad.step(self.path,'agent-1')
        else:self.fail('no gather plan reached')
        inventory=dev.own_observation(self.path,'agent-1')['own_state']['inventory_ug']
        dev.archive(self.path);head=storage.inspect(self.path)['state_hash']
        code='from underworld import adaptive as a; import sys,json; print(json.dumps(a.step(sys.argv[1],"agent-1")))'
        child=subprocess.run([sys.executable,'-c',code,str(self.path)],capture_output=True,text=True,timeout=30)
        self.assertEqual(child.returncode,0,child.stderr)
        self.assertEqual(json.loads(child.stdout)['role'],'gather')
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)
        self.assertEqual(dev.own_observation(self.path,'agent-1')['own_state']['inventory_ug'],inventory)
        self.assertTrue(ad.step(self.path,'agent-1')['goal_completed'])
        self.assertEqual(ad.private(self.path,'agent-1','agent-1')['goals'],1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_missing_online_proof_refuses_an_action_decision(self):
        e=dev.execute(self.path,'agent-1','gather',['resource-1'],{'mass_kg':.001})
        ad.learn_outcome(self.path,'agent-1',e['request']['request_id'])
        with closing(storage._connect(self.path)) as db:
            for seq in e['native_events']:db.execute('DELETE FROM events WHERE seq=?',(int(seq),))
            db.commit()
        with self.assertRaises(ValueError):ad.choose(self.path,'agent-1',['resource-1'])

    def test_scheduler_commit_interruption_does_not_advance_an_actor_twice(self):
        def fail(stage):raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):ad.cohort_step(self.path,fail)
        head=storage.inspect(self.path)['state_hash']
        resumed=ad.cohort_step(self.path)
        self.assertEqual(resumed['cursor'],1)
        self.assertEqual(resumed['agent'],'agent-1')
        self.assertEqual(storage.inspect(self.path)['state_hash'],head)
        self.assertEqual(ad.cohort_step(self.path)['agent'],'agent-2')


class SituatedSequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.base=Path(cls.tmp.name)/'trained.sqlite'
        cls.training=train_locations(cls.base,53)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        self.tmpcase=tempfile.TemporaryDirectory();self.addCleanup(self.tmpcase.cleanup)
        self.path=Path(self.tmpcase.name)/'case.sqlite'
        storage.save(self.base,dev.digest(self._testMethodName)[:20],self.path)

    def test_heldout_location_pair_drives_need_acquisition_and_self_triggered_report(self):
        prepare(self.path,53)
        result=cooperation(self.path,'learned')
        self.assertTrue(result['success'])
        self.assertTrue(result['speech']['spoke'])
        self.assertTrue(all(not x['result']['assigned'] for x in result['steps']))
        self.assertEqual(result['final']['native_rejections'],[])
        self.assertFalse(ad.share_step(self.path,'agent-1')['spoke'])

    def test_whole_message_control_has_no_heldout_named_pair(self):
        prepare(self.path,53)
        self.assertFalse(cooperation(self.path,'whole')['success'])

    def test_depleted_report_cannot_cause_a_second_trip(self):
        prepare(self.path,53,depleted=True)
        first=cooperation(self.path,'learned');self.assertFalse(first['success'])
        position=dev.own_observation(self.path,'agent-2')['own_state']['position_m']
        for _ in range(3):self.assertEqual(ad.step(self.path,'agent-2')['role'],'idle')
        self.assertEqual(dev.own_observation(self.path,'agent-2')['own_state']['position_m'],position)
        self.assertEqual(ad.audit(self.path)['people']['agent-2']['adaptive']['goals'],0)

    def test_stale_message_is_refused_before_navigation(self):
        prepare(self.path,53);self.assertTrue(ad.share_step(self.path,'agent-1')['spoke'])
        for _ in range(2):dev.execute(self.path,'agent-2','rest',duration=40,update_memory=False)
        position=dev.own_observation(self.path,'agent-2')['own_state']['position_m']
        self.assertEqual(ad.step(self.path,'agent-2')['role'],'idle')
        self.assertEqual(dev.own_observation(self.path,'agent-2')['own_state']['position_m'],position)


if __name__=='__main__':unittest.main()
