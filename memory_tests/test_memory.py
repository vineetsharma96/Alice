from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import emotional_memory as memory,memory_store as store,mood_store,weather_store as weather
from underworld.weather_runtime import load,climate


class MemoryTests(unittest.TestCase):
    def observation(self):
        w=load().World(seed=53,population=2,width=32,height=32,dt=.25,scripted=False,bodies=True)
        w.configure_climate(climate());return w.observe_batch(['agent-1'])[0]

    def interval(self,s,o,ident,harm=False):
        after=deepcopy(o);after['tick']=str(int(o['tick'])+40)
        if harm:after['own_state']['weather']['cold_burden']=min(1,o['own_state']['weather']['cold_burden']+.12)
        memory.update(s,o,after,ident);return after

    def test_salience_bounded_retention_and_immutable_facts(self):
        o=self.observation();s=memory.initial(o);o=self.interval(s,o,'harm',True)
        factual=deepcopy(s['emotional_memory']['entries'][0])
        for i in range(80):o=self.interval(s,o,'safe-'+str(i))
        self.assertEqual(len(s['emotional_memory']['entries']),32)
        self.assertEqual(s['emotional_memory']['encoded'],81)
        self.assertEqual(s['emotional_memory']['evicted'],49)
        self.assertEqual(factual,next(e for e in s['emotional_memory']['entries'] if e['event']=='harm'))
        self.assertGreater(factual['salience'],s['emotional_memory']['entries'][-1]['salience'])
        self.assertIsNone(memory.update(s,o,o,'safe-79'))

    def test_relevance_correction_and_observer_labels(self):
        o=self.observation();s=memory.initial(o);o=self.interval(s,o,'harm',True)
        key=memory.affect.cue(o);p=memory.retrieve(s,key)
        fact=deepcopy(s['emotional_memory']['entries'][0])
        self.assertLess(p['value'],-.5);self.assertEqual(memory.retrieve(s,'unrelated')['confidence'],0)
        # Bodily fixture: allow cold recovery without modifying historical records.
        o['own_state']['weather']['cold_burden']=0
        for i in range(20):o=self.interval(s,o,'safe-'+str(i))
        self.assertGreater(memory.retrieve(s,key)['value'],0)
        self.assertEqual(fact,s['emotional_memory']['entries'][0])
        clean=deepcopy(s);labelled=deepcopy(o);labelled['observer_label']='malicious monster';labelled['other_private_mood']=-1
        from underworld import weather_policy
        self.assertEqual(memory.influence(o,s,weather_policy.option()),memory.influence(labelled,clean,weather_policy.option()))

    def test_foreign_clock_parameters_and_modes(self):
        o=self.observation();s=memory.initial(o);foreign=deepcopy(o);foreign['agent_id']='agent-2'
        with self.assertRaises(ValueError):memory.update(s,o,foreign,'x')
        with self.assertRaises(ValueError):memory.influence(foreign,s,{})
        with self.assertRaises(ValueError):memory.initial(o,memory_mode='unknown')
        frozen=memory.initial(o,memory_mode='frozen');self.interval(frozen,o,'safe')
        self.assertEqual(frozen['emotional_memory']['entries'],[])
        s['emotional_memory']['encoded']=-1
        with self.assertRaises(ValueError):memory.validate(s)

    def test_inherited_f4_atomic_retry_pending_and_fresh_resume(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);base=root/'base';old=root/'old';new=root/'new';copy=root/'copy'
            weather.initialize(base,population=2);mood_store.attach(base,old)
            mood_store.commit(old,dict(kind='emotion-policy',agent='agent-1'),'p')
            previous=mood_store.inspect(old);original=old.read_bytes();now=store.attach(old,new)
            self.assertEqual(original,old.read_bytes());self.assertEqual(previous['snapshot'],now['snapshot'])
            for a in previous['people']:
                for k,v in previous['people'][a].items():self.assertEqual(v,now['people'][a][k])
            with closing(weather.connect(new)) as db:
                self.assertEqual(json.loads(store.head(db)[3]['origin'])['scheduler_cursor'],1)
            from underworld.weather_tools import request
            req=request(store.JournalWorld(new),'rest',duration=5)
            store.commit(new,dict(kind='submit',request=req,principal='agent-1'),'submit')
            store.commit(new,dict(kind='step',ticks=7),'partial');weather.save(new,copy)
            store.commit(new,dict(kind='step',ticks=13),'finish')
            r=subprocess.run([sys.executable,'scripts/memory.py','step','--db',str(copy),'--ticks','13','--id','finish'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(store.inspect(new),store.inspect(copy))
            before=store.inspect(new)
            def fault(_):raise RuntimeError('interrupt')
            with self.assertRaises(RuntimeError):store.commit(new,dict(kind='step',ticks=4),'fault',fault)
            self.assertEqual(before,store.inspect(new));store.commit(new,dict(kind='step',ticks=13),'finish')
            self.assertEqual(before,store.inspect(new));self.assertTrue(store.replay(new)['verified'])
            self.assertIsNone(before['people']['agent-2']['last']['appraisal']['goal'])

    def test_disabled_matches_original_native_policy(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'base';new=Path(td)/'new';weather.initialize(base,population=1)
            store.attach(base,new,mode='disabled')
            for i in range(4):
                a=weather.commit(base,dict(kind='policy',agent='agent-1'))
                b=store.commit(new,dict(kind='emotion-policy',agent='agent-1'),str(i))
                self.assertEqual(weather.dumps(a),weather.dumps(b['native']))
            self.assertEqual(store.inspect(new)['people']['agent-1']['emotional_memory']['entries'],[])


if __name__=='__main__':unittest.main()
