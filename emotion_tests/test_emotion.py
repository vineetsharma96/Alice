from copy import deepcopy
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import emotion, emotion_store as store, weather_store as weather
from underworld.weather_runtime import load, climate
from underworld.weather_tools import request


class EmotionTests(unittest.TestCase):
    def world(self):
        w=load().World(seed=53,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True)
        w.configure_climate(climate())
        return w

    def test_native_need_relief_goal_appraisal_and_distinct_rejections(self):
        w=self.world();o=w.observe_batch(['agent-1'])[0]
        r=request(w,'gather','resource-1',dict(mass_kg=.05))
        self.assertEqual(w.submit(r,'agent-1')['status'],'accepted');w.step(4)
        r=request(w,'eat',parameters=dict(mass_kg=.05),duration=2)
        before=w.observe_batch(['agent-1'])[0]
        self.assertEqual(w.submit(r,'agent-1')['status'],'accepted');w.step(8)
        after=w.observe_batch(['agent-1'])[0];receipt=after['recent_action_results'][-1]
        p=dict(value=0,confidence=0,memories=[])
        food=emotion.appraisal(before,after,receipt,'urgent_food',p)
        roof=emotion.appraisal(before,after,receipt,'build_simple_shelter',p)
        self.assertGreater(food['benefit'],roof['benefit'])
        # Real native validators, no fabricated outcome labels.
        far=request(w,'gather','resource-4',dict(mass_kg=.05))
        # resource-4 is stone: choose distant food after a real move instead.
        move=request(w,'move',parameters=dict(x_m=2,y_m=5),duration=2)
        w.submit(move,'agent-1');w.step(8)
        far=request(w,'gather','resource-1',dict(mass_kg=.05))
        out=w.submit(far,'agent-1');self.assertEqual(out['error_code'],'OUT_OF_REACH')
        self.assertEqual(emotion.appraisal(after,after,out,None,p)['classification'],'approach_error')
        empty=request(w,'eat',parameters=dict(mass_kg=.05),duration=2)
        scarce=w.submit(empty,'agent-1');self.assertEqual(scarce['error_code'],'INSUFFICIENT_RESOURCE')
        self.assertEqual(emotion.appraisal(after,after,scarce,None,p)['classification'],'scarcity')
        rest=request(w,'rest',duration=2);w.submit(rest,'agent-1')
        busy=w.submit(request(w,'rest',duration=1,ident='other'),'agent-1')
        self.assertEqual(busy['error_code'],'BUSY')
        self.assertEqual(emotion.appraisal(after,after,busy,None,p)['classification'],'contention')

    def test_time_rate_bounds_privacy_and_duplicate_interval(self):
        w=self.world();o=w.observe_batch(['agent-1'])[0]
        states=[]
        for increment in (1,10):
            s=emotion.initial(o);before=deepcopy(o)
            for t in range(increment,121,increment):
                after=deepcopy(o);after['tick']=str(t*4)
                emotion.update(s,before,after,str(t));before=after
            states.append(s)
        for k in states[0]['affect']:self.assertAlmostEqual(states[0]['affect'][k],states[1]['affect'][k],places=12)
        self.assertAlmostEqual(states[0]['stress'],states[1]['stress'],places=12)
        s=emotion.initial(o);after=deepcopy(o);after['tick']='4'
        changed=deepcopy(after);changed['observer_label']='fear';changed['foreign_private_mood']=1
        a,b=deepcopy(s),deepcopy(s)
        emotion.update(a,o,after,'one');emotion.update(b,o,changed,'one');self.assertEqual(a,b)
        before=deepcopy(a)
        # Public API duplicate returns only if at the already-updated clock.
        emotion.update(a,after,after,'one');self.assertEqual(a,before)
        foreign=deepcopy(after);foreign['agent_id']='agent-2'
        with self.assertRaises(ValueError):emotion.update(a,after,foreign,'foreign')
        self.assertLessEqual(len(states[0]['recent']),64)
        for malformed in (float('nan'),float('inf')):
            with self.assertRaises(ValueError):emotion.clamp(malformed)

    def test_disabled_equivalence_atomic_retry_drift_and_source_save_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite';live=root/'live.sqlite'
            weather.initialize(source,population=1)
            original=source.read_bytes();store.attach(source,live,mode='disabled')
            self.assertEqual(original,source.read_bytes())
            for i in range(6):
                expected=weather.commit(source,dict(kind='policy',agent='agent-1'))
                actual=store.commit(live,dict(kind='emotion-policy',agent='agent-1'),f'p{i}')
                self.assertEqual(weather.dumps(expected),weather.dumps(actual['native']))
            self.assertEqual(weather.inspect(source)['state_hash'],weather.inspect(live)['state_hash'])
            self.assertEqual(weather.inspect(source)['policy'],weather.inspect(live)['policy'])
            before=store.inspect(live)
            again=store.commit(live,dict(kind='emotion-policy',agent='agent-1'),'p5')
            self.assertEqual(before,store.inspect(live));self.assertEqual(actual,again)
            with self.assertRaises(ValueError):store.commit(live,dict(kind='step',ticks=1),'p5')
            def fail(_):raise RuntimeError('simulated interruption before commit')
            with self.assertRaises(RuntimeError):store.commit(live,dict(kind='step',ticks=7),'crash',fail)
            self.assertEqual(before,store.inspect(live))
            self.assertTrue(store.replay(live)['verified'])
            weather.commit(live,dict(kind='step',ticks=1))
            with self.assertRaises(ValueError):store.inspect(live)

    def test_mid_action_fresh_process_resume_and_private_learning_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.sqlite';live=root/'live.sqlite';copy=root/'copy.sqlite'
            weather.initialize(source,population=1,guided=True)
            store.attach(source,live)
            w=store.JournalWorld(live)
            pending=request(w,'rest',duration=5)
            store.commit(live,dict(kind='submit',request=pending,principal='agent-1'),'pending')
            store.commit(live,dict(kind='step',ticks=7),'partial')
            weather.save(live,copy)
            store.commit(live,dict(kind='step',ticks=13),'finish')
            result=subprocess.run([sys.executable,'scripts/emotion.py','step','--db',str(copy),'--ticks','13','--id','finish'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(store.inspect(live),store.inspect(copy))
            self.assertTrue(store.replay(copy)['verified'])
            with closing(weather.connect(copy,False)) as db:
                db.execute("UPDATE emotion_operations SET after_hash='corrupt' WHERE logical_id='finish'")
            with self.assertRaises(ValueError):store.replay(copy)

    def test_other_person_never_receives_actors_private_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source.sqlite';live=Path(tmp)/'live.sqlite'
            weather.initialize(src,population=2)
            store.attach(src,live,agents=['agent-1','agent-2'])
            store.commit(live,dict(kind='emotion-policy',agent='agent-1'),'one')
            x=store.inspect(live)['people']
            self.assertIsNotNone(x['agent-1']['last']['appraisal']['goal'])
            self.assertIsNone(x['agent-2']['last']['appraisal']['goal'])
            self.assertNotEqual(x['agent-1']['recent'],x['agent-2']['recent'])
            self.assertEqual(x['agent-1']['tick'],x['agent-2']['tick'])
            self.assertTrue(store.replay(live)['verified'])

    def test_native_contention_bounds_emotional_retries(self):
        from underworld.weather_tools import roof,execute,walk
        w=self.world();roof(w)
        walk(w,[2,3])
        for material,target,action,n,duration in [('water','resource-2','drink',3,1),('food','resource-1','eat',2,2)]:
            for _ in range(n):
                execute(w,'gather',target,dict(mass_kg=.05))
                execute(w,action,parameters=dict(mass_kg=.05),duration=duration)
        walk(w,[4,6])
        o=w.observe_batch(['agent-1'])[0];person=emotion.initial(o)
        # Deliberately seeded cognition UNIT FIXTURE, not acquired-experience evidence.
        person['associations'][emotion.cue(o)]=dict(value=-.7,confidence=.8,seconds=120,evidence=['unit-fixture'])
        w.submit(request(w,'rest',duration=40),'agent-1')
        people={'agent-1':person};policies={}
        for i in range(3):
            r=store.apply(w,policies,people,dict(kind='emotion-policy',agent='agent-1'),f'busy-{i}',lambda c:weather.apply(w,c,policies))
            self.assertTrue(r['influence']['changed'])
            self.assertEqual(r['native']['receipt']['error_code'],'BUSY')
        self.assertGreater(person['caution_blocked_until'],int(o['tick']))
        r=store.apply(w,policies,people,dict(kind='emotion-policy',agent='agent-1'),'cooldown',lambda c:weather.apply(w,c,policies))
        self.assertFalse(r['influence']['changed'])


if __name__=='__main__':unittest.main()
