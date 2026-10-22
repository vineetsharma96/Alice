from contextlib import closing
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from underworld import emotion_store as legacy,mood_store as store,mood_affect as affect,weather_store as weather
from underworld.weather_runtime import climate,load
from underworld.weather_tools import request,execute,roof,walk


class MoodTests(unittest.TestCase):
    def world(self):
        w=load().World(seed=53,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True)
        w.configure_climate(climate());return w

    def test_parameters_and_single_rate_aware_pipeline(self):
        for bad in ('unknown',{},dict(affect.PRESETS['balanced'],sensitivity=True),dict(affect.PRESETS['balanced'],rise_s=float('nan'))):
            with self.assertRaises(ValueError):affect.temperament(bad)
        o=self.world().observe_batch(['agent-1'])[0];o['own_state']['body']['hunger']=.8
        results=[]
        for interval in (1,10):
            s=affect.initial(o);prior=deepcopy(o)
            for t in range(interval,121,interval):
                after=deepcopy(o);after['tick']=str(t*4)
                affect.update(s,prior,after,str(t));prior=after
            results.append(s)
        self.assertAlmostEqual(results[0]['stress'],results[1]['stress'],places=12)
        self.assertAlmostEqual(results[0]['mood']['valence'],results[1]['mood']['valence'],places=12)
        # Exactly one slow integrator: old tau120 raw discomfort is not added.
        import math
        self.assertAlmostEqual(results[0]['stress'],((.8-.3)/.7)*(1-math.exp(-1)),places=12)

    def test_inherited_history_source_bytes_scheduler_and_exact_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);weather_path=root/'w.sqlite';old=root/'old.sqlite';new=root/'mood.sqlite';copy=root/'copy.sqlite'
            weather.initialize(weather_path,population=2)
            legacy.attach(weather_path,old,agents=['agent-1','agent-2'])
            legacy.commit(old,dict(kind='emotion-policy',agent='agent-1'),'first')
            previous=legacy.inspect(old);before=old.read_bytes()
            now=store.attach(old,new)
            self.assertEqual(before,old.read_bytes());self.assertEqual(previous['snapshot'],now['snapshot'])
            for a,person in previous['people'].items():
                for key in ('associations','recent','episodes','stress','updates','affect'):
                    self.assertEqual(person[key],now['people'][a][key])
            with closing(weather.connect(new)) as db:
                _,_,_,meta=store.head(db)
                self.assertEqual(json.loads(meta['origin'])['scheduler_cursor'],1)
            w=store.JournalWorld(new);pending=request(w,'rest',duration=5)
            store.commit(new,dict(kind='submit',request=pending,principal='agent-1'),'pending')
            store.commit(new,dict(kind='step',ticks=7),'partial')
            weather.save(new,copy)
            store.commit(new,dict(kind='step',ticks=13),'finish')
            r=subprocess.run([sys.executable,'scripts/mood.py','step','--db',str(copy),'--ticks','13','--id','finish'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(store.inspect(new),store.inspect(copy))
            self.assertTrue(store.replay(new)['verified'])
            after=store.inspect(new)
            def fault(_):raise RuntimeError('interrupted')
            with self.assertRaises(RuntimeError):store.commit(new,dict(kind='step',ticks=4),'fault',fault)
            self.assertEqual(after,store.inspect(new))
            again=store.commit(new,dict(kind='step',ticks=13),'finish')
            self.assertEqual(after,store.inspect(new));self.assertIsNotNone(again)
            self.assertIsNone(after['people']['agent-2']['last']['appraisal']['goal'])

    def test_bounded_authored_mood_influence_uses_native_executor(self):
        w=self.world();roof(w);walk(w,[2,3])
        for kind,target,action,n,duration in [('water','resource-2','drink',3,1),('food','resource-1','eat',2,2)]:
            for _ in range(n):execute(w,'gather',target,dict(mass_kg=.05));execute(w,action,parameters=dict(mass_kg=.05),duration=duration)
        walk(w,[4,6]);o=w.observe_batch(['agent-1'])[0]
        high=affect.initial(o);high['stress']=.8;high['mood']['valence']=-.8
        # Explicit cognitive fixture, not naturally learned evidence.
        high['associations'][affect.cue(o)]=dict(value=-.10,confidence=.8,seconds=120,evidence=['unit-fixture'])
        disconnected=deepcopy(high);disconnected['mood_connected']=False
        from underworld import weather_policy
        base=weather_policy.option()
        movement,log=affect.influence(o,high,base)
        self.assertEqual(movement['action'],'move');self.assertAlmostEqual(log['caution_threshold'],-.088)
        self.assertIsNone(affect.influence(o,disconnected,base)[0])
        r=store.apply(w,{}, {'agent-1':high},dict(kind='emotion-policy',agent='agent-1'),'mood-probe',lambda c:weather.apply(w,c,{}))
        self.assertEqual(r['native']['receipt']['status'],'completed')
        self.assertTrue(w.observe_batch(['agent-1'])[0]['own_state']['weather']['shelter_id'])

    def test_disabled_keeps_exact_weather_actions_and_bounds(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);base=root/'base.sqlite';new=root/'mood.sqlite'
            weather.initialize(base,population=1);store.attach(base,new,mode='disabled')
            for i in range(6):
                expected=weather.commit(base,dict(kind='policy',agent='agent-1'))
                actual=store.commit(new,dict(kind='emotion-policy',agent='agent-1'),f'p{i}')
                self.assertEqual(weather.dumps(expected),weather.dumps(actual['native']))
            self.assertEqual(weather.inspect(base)['state_hash'],weather.inspect(new)['state_hash'])
            self.assertEqual(store.inspect(new)['people']['agent-1']['stress'],0)


if __name__=='__main__':unittest.main()
