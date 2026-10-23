from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from underworld import life_store as store, life_affect, weather_store as weather
from underworld import weather_policy as policy, weather_tools as tools
from underworld import communication_f9 as communication
from scripts.life import run,report


class IntegratedLifeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.source=self.root/'source.sqlite';self.path=self.root/'life.sqlite'
        store.initialize_source(self.source,seed=61,population=4)

    def attach(self,mode='connected'):
        return store.attach(self.source,self.path,mode=mode)

    def setup_social(self):
        w=tools.JournalWorld(self.source)
        tools.walk(w,[3.1,3],agent='agent-2')
        self.assertEqual(tools.execute(w,'gather','resource-1',dict(mass_kg=.2))['status'],'completed')

    def test_atomic_native_grounded_directional_help_and_actual_reciprocation(self):
        self.setup_social();original=self.source.read_bytes();self.attach()
        r=store.act(self.path,'agent-1',policy.option('give',dict(material='food',mass_kg=.15),'agent-2',1,'assigned_transfer'),'help')
        self.assertEqual(r['native']['receipt']['status'],'completed')
        people=store.inspect(self.path)['people']
        recipient=people['agent-2']['life'];donor=people['agent-1']['life']
        self.assertGreater(recipient['relationships']['agent-1']['trust'],0)
        self.assertNotIn('agent-2',donor['relationships'])
        self.assertIn('gratitude',recipient['social']['states'])
        self.assertFalse(people['agent-3']['life']['relationships'])
        r=store.commit(self.path,dict(kind='emotion-policy',agent='agent-2'),'reciprocate')
        self.assertEqual(r['native']['request']['action_type'],'give')
        self.assertEqual(r['native']['receipt']['status'],'completed')
        self.assertEqual(original,self.source.read_bytes())
        self.assertTrue(store.replay(self.path)['verified'])

    def test_speech_is_natively_delivered_and_receiver_lexicon_starts_private(self):
        self.setup_social();self.attach()
        before=store.inspect(self.path)['people']
        self.assertFalse(before['agent-2']['life']['communication']['comprehension'])
        for i in range(6):
            state=store.inspect(self.path)['people']['agent-1']['life']['communication']
            token=communication.emit(deepcopy(state),'calm','agent-2','preview')['token']
            r=store.act(self.path,'agent-1',policy.option('speak',dict(text=token),duration=1,goal='assigned_native_signal'),f'signal-{i}')
            self.assertEqual(r['native']['receipt']['status'],'completed')
        people=store.inspect(self.path)['people'];listener=people['agent-2']['life']
        self.assertEqual(listener['deliveries'],6)
        self.assertEqual(listener['grounded'],6)
        prediction=communication._interpret(listener['communication'],'agent-1',token)
        self.assertEqual(prediction['meaning'],'calm')
        self.assertGreater(prediction['confidence'],.8)
        self.assertEqual(communication._interpret(listener['communication'],'agent-3',token)['meaning'],None)
        self.assertTrue(store.replay(self.path)['verified'])

    def test_frozen_side_modules_do_not_learn_and_disconnected_preserves_actions(self):
        self.setup_social();self.attach(mode='frozen')
        store.act(self.path,'agent-1',policy.option('give',dict(material='food',mass_kg=.15),'agent-2',1,'assigned_transfer'),'help')
        person=store.inspect(self.path)['people']['agent-2']['life']
        self.assertFalse(person['relationships']);self.assertEqual(person['help_received'],0)
        self.assertTrue(store.replay(self.path)['verified'])

    def test_exact_action_interval_and_native_value_learning(self):
        self.attach()
        r=store.act(self.path,'agent-1',policy.option(duration=5,goal='assigned_recovery'),'rest')
        state=store.inspect(self.path)['people']['agent-1']
        self.assertEqual(state['life']['regulation']['evidence'][-1]['elapsed_s'],5)
        self.assertIn('recovery',state['life']['values']['acquired_preferences'])
        self.assertTrue(state['emotional_memory']['entries'])
        self.assertEqual(state['tick'],int(r['native']['after']['tick']))

    def test_rollback_idempotence_resume_every_actor_and_fresh_process(self):
        self.attach();before=store.inspect(self.path)
        def fail(_):raise RuntimeError('injected failure')
        with self.assertRaises(RuntimeError):store.commit(self.path,dict(kind='emotion-policy',agent='agent-1'),'fault',fault=fail)
        self.assertEqual(before,store.inspect(self.path))
        result=run(self.path,30);self.assertEqual(set(result['scheduled_turns']),set(before['people']))
        backup=self.root/'backup.sqlite';weather.save(self.path,backup)
        self.assertEqual(store.next_turn(self.path),store.next_turn(backup))
        a=run(self.path,40);b=run(backup,40)
        self.assertEqual(a['source_hash'],b['source_hash'])
        fresh=subprocess.run([sys.executable,'-c','from underworld.life_store import replay;import sys;print(replay(sys.argv[1])["verified"])',str(backup)],capture_output=True,text=True,check=True)
        self.assertEqual(fresh.stdout.strip(),'True')

    def test_private_state_injection_refused_and_emergency_choices_protected(self):
        self.attach();s=store.inspect(self.path)['people']['agent-1']
        with closing(weather.connect(self.path)) as db:o=store.head(db)[0].observe_batch(['agent-1'])[0]
        corrupted=deepcopy(s);corrupted['life']['communication']['owner']='agent-2'
        with self.assertRaises(ValueError):life_affect.validate(corrupted)
        base=policy.option('eat',dict(mass_kg=.05),duration=2,goal='urgent_food')
        alternate,_=life_affect.influence(o,s,base);self.assertIsNone(alternate)
        from underworld.life_viewer import packet
        packet(self.path,'agent-1')
        self.assertEqual(s,store.inspect(self.path)['people']['agent-1'])

    def test_existing_f5_people_and_scheduler_are_inherited_without_reset(self):
        from underworld import memory_store
        f5=self.root/'f5.sqlite';memory_store.attach(self.source,f5)
        memory_store.commit(f5,dict(kind='emotion-policy',agent='agent-1'),'earlier')
        before=memory_store.inspect(f5);raw=f5.read_bytes()
        store.attach(f5,self.path)
        after=store.inspect(self.path)
        self.assertEqual(before['snapshot'],after['snapshot'])
        for agent,person in before['people'].items():
            inherited=deepcopy(after['people'][agent]);inherited.pop('life')
            self.assertEqual(person,inherited)
        self.assertEqual(store.next_turn(self.path)[1],1)
        self.assertEqual(raw,f5.read_bytes())
        self.assertTrue(store.replay(self.path)['verified'])

    def test_pending_native_action_survives_enrollment_and_mid_plan_backup(self):
        world=tools.JournalWorld(self.source)
        request=tools.request(world,'rest',duration=10)
        self.assertEqual(world.submit(request,'agent-1')['status'],'accepted')
        self.attach();store.commit(self.path,dict(kind='step',ticks=20),'half')
        self.assertTrue(store.JournalWorld(self.path).observe_batch(['agent-1'])[0]['own_state']['busy'])
        backup=self.root/'pending-backup.sqlite';weather.save(self.path,backup)
        for path in (self.path,backup):store.commit(path,dict(kind='step',ticks=20),'finish')
        self.assertEqual(store.inspect(self.path)['hash'],store.inspect(backup)['hash'])
        self.assertFalse(store.JournalWorld(self.path).observe_batch(['agent-1'])[0]['own_state']['busy'])
        self.assertTrue(store.replay(backup)['verified'])


if __name__=='__main__':unittest.main()
