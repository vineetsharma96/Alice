from pathlib import Path
import tempfile
import unittest

from underworld import weather_policy as policy, weather_store as store
from underworld.weather_runtime import climate, load
from weather_tests.helpers import ingredients, move, roof, walk


class WeatherPolicyTests(unittest.TestCase):
    def world(self):
        w=load().World(seed=53,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True)
        w.configure_climate(climate(temperature_bias_c=-25))
        return w

    def test_own_senses_do_not_disclose_future_or_hidden_shelter(self):
        w=self.world();roof(w);move(w,[4,14])
        o=w.observe_batch(['agent-1'])[0];env=o['own_state']['weather']
        self.assertEqual(env['observed_shelters'],[])
        self.assertFalse(set(env)&{'rng','target','next_change_s','season'})
        s=policy.state();policy.choose(o,s)
        self.assertFalse(any(e['entity']['kind']=='lean_to' for e in s['memory'].values()))
        s['memory']['fake']=dict(observer='agent-2',source='own_native_observation',tick=0,entity={})
        with self.assertRaises(ValueError):policy.choose(o,s)

    def test_authored_response_reaches_observed_roof(self):
        w=self.world();target,_=roof(w);policies={}
        for _ in range(24):
            result=policy.advance(w,policies,'agent-1')
            self.assertEqual(result['receipt']['status'],'completed')
            if result['after']['own_state']['weather']['shelter_id']==target:break
        self.assertEqual(w.observe_batch(['agent-1'])[0]['own_state']['weather']['shelter_id'],target)
        self.assertTrue(all(x['observer']=='agent-1' for x in policies['agent-1']['memory'].values()))

    def test_assigned_build_uses_real_prerequisites_and_need_preemption(self):
        w=self.world();ingredients(w);policies={}
        for n in range(32):
            r=policy.advance(w,policies,'agent-1',assignment=dict(goal='build_simple_shelter',position_m=[4,4]) if n==0 else None)
            self.assertEqual(r['receipt']['status'],'completed')
            if any(s['complete'] for s in w.weather_snapshot()['shelters']):break
        self.assertTrue(any(s['complete'] for s in w.weather_snapshot()['shelters']))
        self.assertTrue(any(x.get('origin')=='operator_assigned' for x in policies['agent-1']['completed']))
        o=w.observe_batch(['agent-1'])[0]
        o['own_state']['body']['thirst']=.9
        policies['agent-1']['goal']='build_simple_shelter'
        c=policy.choose(o,policies['agent-1'])
        self.assertNotEqual(c['action'],'work_construction')
        self.assertGreater(policies['agent-1']['preemptions'],0)

    def test_policy_save_resume_and_native_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'world.sqlite';copy=Path(directory)/'copy.sqlite'
            store.initialize(p,population=1,configuration=climate(temperature_bias_c=-15))
            for _ in range(4):store.commit(p,dict(kind='policy',agent='agent-1'))
            store.save(p,copy)
            for target in (p,copy):
                for _ in range(4):store.commit(target,dict(kind='policy',agent='agent-1'))
            self.assertEqual(store.inspect(p),store.inspect(copy))
            self.assertTrue(store.replay(p)['replay_matches'])

    def test_local_scarcity_search_and_blocked_sites_stop_without_building(self):
        w=self.world();o=w.observe_batch(['agent-1'])[0]
        o['visible_entities']=[]
        o['own_state']['body'].update(hunger=.1,thirst=.1)
        s=policy.state();s['assigned']=dict(goal='build_simple_shelter')
        for _ in range(25):policy.choose(o,s)
        self.assertTrue(any(x.get('reason')=='local_material_search_budget' for x in s['completed']))
        self.assertEqual(w.weather_snapshot()['shelters'],[])

    def test_four_people_settle_without_routine_need_oscillation(self):
        w=load().World(seed=53,population=4,width=32,height=32,dt=.25,scripted=False,bodies=True)
        w.configure_climate(climate(temperature_bias_c=-25))
        for i in range(2,5):walk(w,[8,3+i],f'agent-{i}')
        roof(w)
        for i,q in enumerate(([2.6,4],[4,2.6],[5.4,4],[4,5.4]),1):walk(w,q,f'agent-{i}')
        states={};maximum=0
        for i in range(32):
            policy.advance(w,states,f'agent-{i%4+1}')
            maximum=max(maximum,sum(bool(e['shelter_id']) for e in w.weather_snapshot()['exposure'].values()))
        self.assertEqual(maximum,4)


if __name__=='__main__':unittest.main()
