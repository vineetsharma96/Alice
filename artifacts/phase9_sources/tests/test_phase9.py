from contextlib import closing
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from underworld import storage
from underworld.learning import PolicyStore, features, request, execute, label_receipt, control, sha, update, world_head, registration
from scripts.phase9_experiment import prepare, clone, summarize, bootstrap


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.store=PolicyStore.create(self.root/'policy.sqlite',11)

    def tearDown(self): self.tmp.cleanup()

    def world(self, mass=0): return prepare(self.root/'world.sqlite',11,'eat',mass)

    def test_registration_is_sealed(self):
        spec,seal=registration()
        self.assertEqual(spec['seeds'],[11,22,33,44,55]); self.assertEqual(len(seal['study_sha256']),64)

    def test_native_negative_updates_and_restart_replay(self):
        path=self.world()
        record=self.store.train(path,'eat',.2,'test-negative')
        self.assertFalse(record['label']); self.assertNotEqual(record['before_weights'],record['after_weights'])
        self.assertEqual(self.store.read()['version'],1)
        self.assertEqual(PolicyStore(self.store.path).read(),self.store.read())
        storage.replay(path)
        run=subprocess.run([sys.executable,'-m','underworld.learning','status','--db',str(self.store.path)],capture_output=True,text=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout)['version'],1)

    def test_crash_after_native_commit_applies_exactly_once(self):
        path=self.world(); req=self.store.reserve(path,'eat',.2,'crash-after')
        execute(path,req)
        reopened=PolicyStore(self.store.path); reopened.finish(path,'crash-after'); before=sha(reopened.read())
        reopened.finish(path,'crash-after')
        self.assertEqual(before,sha(reopened.read())); self.assertEqual(reopened.read()['version'],1)

    def test_crash_before_submission_stays_reserved_and_never_replays(self):
        path=self.world(); self.store.reserve(path,'eat',.2,'unsubmitted'); head=world_head(path)[3]
        with self.assertRaisesRegex(ValueError,'committed request'): self.store.finish(path,'unsubmitted')
        self.assertEqual(world_head(path)[3],head); self.assertEqual(self.store.read()['version'],0)
        with self.assertRaisesRegex(ValueError,'unresolved'): self.store.reserve(path,'eat',.2,'new')

    def test_accepted_but_incomplete_is_not_positive(self):
        path=self.world(.4); req=self.store.reserve(path,'eat',.2,'partial')
        storage.advance(path,1,[(int(req['observation_version']),req)])
        with self.assertRaisesRegex(ValueError,'incomplete'): self.store.finish(path,'partial')
        self.assertEqual(self.store.read()['version'],0)
        storage.advance(path,9); record=self.store.finish(path,'partial')
        self.assertTrue(record['label'])

    def test_foreign_path_and_changed_head_rejected(self):
        path=self.world(); req=self.store.reserve(path,'eat',.2,'source')
        execute(path,req); other=self.root/'other.sqlite'; clone(path,other)
        with self.assertRaisesRegex(ValueError,'foreign world'): self.store.finish(other,'source')
        storage.advance(path,1)
        with self.assertRaisesRegex(ValueError,'source/head mismatch'): self.store.finish(path,'source')

    def test_forged_or_missing_request_is_not_evidence(self):
        path=self.world(); req=self.store.reserve(path,'eat',.2,'source'); execute(path,req)
        with closing(sqlite3.connect(path)) as db:
            db.execute("UPDATE decisions SET source='operator' WHERE id=(SELECT max(id) FROM decisions)"); db.commit()
        with self.assertRaisesRegex(ValueError,'foreign committed request'): self.store.finish(path,'source')

    def test_checksum_and_recomputed_update_chain(self):
        self.store.train(self.world(),'eat',.2,'source')
        with closing(sqlite3.connect(self.store.path)) as db:
            state=json.loads(db.execute('SELECT payload FROM policy').fetchone()[0]); state['weights'][0]=7
            db.execute('UPDATE policy SET payload=?',(json.dumps(state),)); db.commit()
        with self.assertRaisesRegex(ValueError,'integrity'): self.store.read()
        with closing(sqlite3.connect(self.store.path)) as db:
            db.execute('UPDATE policy SET checksum=?',(sha(state),)); db.commit()
        with self.assertRaisesRegex(ValueError,'parameter/version'): self.store.read()

    def test_readonly_evaluation_and_memory_ties(self):
        s=self.store.read(); s['records']=[dict(status='finished',x=[.1,.2,1],label=False),dict(status='finished',x=[.3,.2,1],label=True)]
        before=copy.deepcopy(s)
        self.assertFalse(control('nearest_memory',s,[.1,.2,1]))
        self.assertFalse(control('bracket_memory',s,[.1,.2,1]))
        self.assertTrue(control('bracket_memory',s,[.3,.2,1]))
        for arm in ('online','frozen','nearest_memory','bracket_memory'): control(arm,s,[.2,.2,1])
        self.assertEqual(s,before)

    def test_own_senses_only_and_feature_limits(self):
        o=storage.observe(self.world(.4),['agent-1'])[0]
        self.assertEqual(features(o,'eat',.2),[.4,.2,1])
        for mass in (0,1.1,float('nan'),True):
            with self.assertRaises(ValueError): features(o,'eat',mass)
        o['agent_id']='agent-2'
        with self.assertRaises(ValueError): features(o,'eat',.2)

    def test_native_equality_and_conservation(self):
        path=self.world(.4); before=world_head(path)[0].snapshot()['material_totals_ug']
        self.assertTrue(self.store.train(path,'eat',.4,'equality')['label'])
        self.assertEqual(world_head(path)[0].snapshot()['material_totals_ug'],before)

    def test_controls_cannot_pass_gate_by_abstaining(self):
        spec,_=registration(); rows=[]
        for seed in spec['seeds']:
            for stage in ('A_after_A','B_after_B','A_after_B'):
                for arm in spec['arms']:
                    for label in (False,True): rows.append(dict(seed=seed,stage=stage,arm=arm,label=label,
                        prediction=False,requested_kg=.2,receipt={'status':'completed'},ticks=10))
        result=summarize(rows,spec['seeds'],spec['arms'],spec['gate'])
        self.assertEqual(result['primary_means']['online'],.5); self.assertFalse(result['advance'])
        self.assertEqual(bootstrap([0]*5),[0,0])


if __name__=='__main__': unittest.main()
