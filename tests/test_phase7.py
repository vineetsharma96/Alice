import copy
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from underworld import storage,runtime,memory,cognition
from underworld.config import load,validate
from underworld.lease import Lease
from underworld.native import load_native
from underworld.supervisor import run_isolated
from underworld.wire import dumps,loads

ROOT=Path(__file__).resolve().parents[1]


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'data').mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='phase7-test-',dir=ROOT/'data')
        self.path=Path(self.tmp.name)/'run.sqlite'
        self.config=load(ROOT/'config/unattended.toml')
        self.config['world'].update(population=2,population_limit=2)
        self.config['execution'].update(batch_ticks=5,epoch_ticks=10,checkpoint_keep=2,memory_recent=4)

    def tearDown(self):self.tmp.cleanup()
    def create(self):storage.create(self.path,self.config)

    def test_configuration_rejects_unbounded_or_ambiguous_controls(self):
        for key,value in [('epoch_ticks',4),('checkpoint_keep',5),('queue_limit',0),('max_db_bytes',0),('cognition_call_limit',1025),('episodic_memory',1)]:
            config=copy.deepcopy(self.config);config['execution'][key]=value
            with self.assertRaises(ValueError):validate(config)
        for sim,wall in [(float('nan'),5),(1,0),(86401,1),(1,3601)]:
            with self.assertRaises(ValueError):run_isolated(self.path,sim,wall)

    def test_actual_token_required_and_environment_cannot_spoof_it(self):
        self.create()
        os.environ['UNDERWORLD_CONTAINER']='pretend'
        try:
            with self.assertRaisesRegex(ValueError,'AppContainer'):runtime.run(self.path,1,1)
        finally:os.environ.pop('UNDERWORLD_CONTAINER',None)

    def test_rotation_bounds_archives_and_replays_every_retained_epoch(self):
        self.create();storage.save(self.path,'auto-epoch-user')
        for _ in range(4):
            storage._advance(self.path,10);runtime.rotate(self.path)
        self.assertEqual(len(list(Path(str(self.path)+'.epochs').glob('*.sqlite'))),2)
        for path in [self.path,*Path(str(self.path)+'.epochs').glob('*.sqlite')]:self.assertTrue(storage.replay(path)['replay_matches'])
        current=storage.inspect(self.path)
        self.assertEqual(current['event_counts']['tick'],40)
        self.assertEqual(current['event_counts']['history_compacted'],4)
        with closing(storage._connect(self.path,readonly=True)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM decisions').fetchone()[0],0)
            self.assertEqual(runtime.verify_control(db)['epoch'],4)
            self.assertIsNotNone(db.execute("SELECT name FROM checkpoints WHERE name='auto-epoch-user'").fetchone())
            self.assertLessEqual(db.execute("SELECT COUNT(*) FROM episodes WHERE agent='agent-1'").fetchone()[0],4)

    def test_original_reports_and_pending_plan_evidence_survive_pruning(self):
        self.create()
        with closing(storage._connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE')
            for i in range(12):memory.episode(db,'agent-1',f'fixture-{i}',0,'action_result',{'text':str(i)})
            memory.episode(db,'agent-1','source-book',0,'book_read',{'text':'An unverified original report'})
            first=db.execute('SELECT MIN(id) FROM episodes').fetchone()[0]
            db.execute('INSERT INTO plans VALUES(?,?)',('agent-1',dumps({'status':'pending','evidence':[first]})))
            memory.seal(db);db.commit()
        runtime.rotate(self.path)
        with closing(storage._connect(self.path,readonly=True)) as db:
            self.assertIsNotNone(db.execute('SELECT id FROM episodes WHERE id=?',(first,)).fetchone())
            self.assertEqual(db.execute("SELECT COUNT(*) FROM episodes WHERE kind='book_read'").fetchone()[0],1)
            memory.verify(db)

    def test_epoch_and_queue_tampering_is_detected(self):
        self.create();runtime.rotate(self.path)
        with closing(sqlite3.connect(self.path)) as db:
            record=loads(db.execute('SELECT payload FROM runtime_epochs').fetchone()[0]);record['tick']=999
            db.execute('UPDATE runtime_epochs SET payload=?',(dumps(record),))
            db.commit()
        with self.assertRaisesRegex(ValueError,'epoch chain'):storage.inspect(self.path)

    def test_queue_tampering_is_detected(self):
        self.create()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO cognition_queue VALUES('agent-1',0)");db.commit()
        with self.assertRaisesRegex(ValueError,'control checksum'):storage.inspect(self.path)

    @unittest.skipUnless(os.name=='nt','Windows isolation integration')
    def test_parallel_isolated_launches_do_not_overwrite_loaded_dlls(self):
        self.create();other=Path(self.tmp.name)/'other'/'run.sqlite';storage.create(other,self.config)
        results=[];errors=[]
        def launch(path):
            try:results.append(run_isolated(path,30,20))
            except Exception as error:errors.append(str(error))
        threads=[threading.Thread(target=launch,args=(path,)) for path in (self.path,other)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=30)
        self.assertFalse(errors,errors);self.assertEqual(len(results),2)
        self.assertTrue(all(r['status']=='target_reached' and r['isolation_profile']['cleaned'] for r in results),[(r['status'],r.get('error'),r['isolation_profile']) for r in results])

    def test_archive_quota_preserves_committed_head(self):
        self.create();storage._advance(self.path,3);before=storage.inspect(self.path)['state_hash']
        limits=self.config['execution']|{'max_archive_bytes':1}
        with self.assertRaisesRegex(ValueError,'disk quota'):runtime.rotate(self.path,limits)
        self.assertEqual(storage.inspect(self.path)['state_hash'],before)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_rotation_retries_checkpoint_recorded_before_backup_publication(self):
        self.create();storage._advance(self.path,10)
        storage.save(self.path,'auto_epoch_1',_automated=True)
        runtime.rotate(self.path)
        self.assertEqual(runtime.status(self.path)['epoch'],1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])
        with self.assertRaisesRegex(ValueError,'reserved'):storage.save(self.path,'auto_epoch_7')

    def test_sqlite_page_cap_rolls_back_full_transaction(self):
        self.config['execution']['max_db_bytes']=1048576;self.create()
        with closing(storage._connect(self.path)) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE quota_fixture(payload BLOB)')
                db.execute('INSERT INTO quota_fixture VALUES(zeroblob(2097152))')
            db.rollback()
        self.assertLessEqual(self.path.stat().st_size,1048576)
        self.assertEqual(storage.inspect(self.path)['tick'],'0')

    def test_writer_lease_excludes_process_and_releases_after_kill(self):
        self.create()
        script='from underworld.lease import Lease; import sys,time;\nwith Lease(sys.argv[1]):\n print("owned",flush=True);time.sleep(60)'
        child=subprocess.Popen([sys.executable,'-c',script,str(self.path)],stdout=subprocess.PIPE,text=True,cwd=ROOT)
        try:
            self.assertEqual(child.stdout.readline().strip(),'owned')
            with self.assertRaisesRegex(ValueError,'another writer'):storage._advance(self.path,1)
            self.assertEqual(storage.inspect(self.path)['tick'],'0')
        finally:child.kill();child.wait();child.stdout.close()
        storage._advance(self.path,1)

    def test_forced_exit_recovers_exact_commit_and_rotation_boundaries(self):
        script='from underworld import runtime; import os,sys;\ndef fault(stage,tick):\n if stage==sys.argv[2] and tick==int(sys.argv[3]):os._exit(77)\nruntime.run(sys.argv[1],30,20,require_isolation=False,fault=fault)'
        for stage,trigger,expected in [('before_commit',3,2),('after_commit',3,3),('after_checkpoint',10,10),('rotation_before_commit',10,10)]:
            with self.subTest(stage=stage):
                self.path=Path(self.tmp.name)/f'{stage}.sqlite';self.create()
                child=subprocess.run([sys.executable,'-c',script,str(self.path),stage,str(trigger)],cwd=ROOT,capture_output=True,timeout=25)
                self.assertEqual(child.returncode,77,child.stderr.decode())
                storage.recover(self.path);self.assertEqual(int(storage.inspect(self.path)['tick']),expected)
                report=runtime.run(self.path,3,10,require_isolation=False)
                self.assertEqual(int(report['tick']),expected+3)
                self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_queue_caps_quota_and_recovery_do_not_duplicate_inference(self):
        self.config['cognition']['provider']='baseline';self.config['execution'].update(queue_limit=1,cognition_call_limit=1,calls_per_batch=1)
        self.create();runtime.dispatch(self.path,self.config['execution'])
        self.assertEqual(runtime.status(self.path)['queue_dropped'],1)
        with closing(storage._connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE');db.execute("INSERT INTO cognition_queue VALUES('agent-1',0)")
            control=loads(db.execute('SELECT payload FROM runtime_state').fetchone()[0])
            runtime._save_control(db,control);db.commit()
        self.assertEqual(runtime.dispatch(self.path,self.config['execution'])[0]['status'],'recovered_reserved_call')
        with closing(storage._connect(self.path,readonly=True)) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0],1)

    def test_stop_file_and_wall_limit_return_committed_heads(self):
        self.create()
        def stop(stage,tick):
            if stage=='after_commit' and tick==3:runtime.request_stop(self.path)
        report=runtime.run(self.path,100,20,require_isolation=False,fault=stop)
        self.assertEqual((report['status'],report['tick']),('stopped','3'))
        report=runtime.run(self.path,100,.01,require_isolation=False)
        self.assertEqual(report['status'],'wall_limit')
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    @unittest.skipUnless(os.name=='nt','Windows isolation integration')
    def test_os_network_denial_and_explicit_json_inference_pipe(self):
        self.config['cognition']['provider']='llama.cpp';self.config['execution']['cognition_call_limit']=2
        self.create()
        report=run_isolated(self.path,15,20,local_model=True,broker_provider=cognition.Baseline())
        self.assertEqual(report['status'],'target_reached')
        self.assertEqual(report['broker_calls'],2)
        self.assertEqual(report['fallbacks'],0)
        self.assertTrue(report['isolation']['token']['appcontainer'])
        self.assertTrue(all(p['access_denied'] for p in report['isolation']['connections'][:2]))
        self.assertTrue(report['isolation_profile']['cleaned'])


class NativeRetentionTests(unittest.TestCase):
    def test_only_finished_generated_receipts_are_retired_and_cannot_reexecute(self):
        world=load_native().World(population=1,scripted=False,dt=1,bodies=True)
        def request(rid,duration=1):
            o=world.observe_batch(['agent-1'])[0]
            return {'schema_version':1,'run_id':o['run_id'],'request_id':rid,'agent_id':'agent-1','observation_version':o['tick'],
                'action_type':'rest','target_ids':[],'parameters':{},'requested_duration':duration}
        old=request('utility-0-agent-1');self.assertEqual(world.submit(old,'agent-1')['status'],'accepted');world.step(1)
        external=request('external-receipt');world.submit(external,'agent-1');world.step(1)
        pending=request('utility-2-agent-1',5);world.submit(pending,'agent-1')
        self.assertEqual(world._compact_history(),1)
        self.assertEqual(world.submit(external,'agent-1')['status'],'completed')
        world.step(5)
        self.assertEqual(world.submit(old,'agent-1')['error_code'],'STALE_OBSERVATION')
        self.assertEqual(world.submit(old|{'observation_version':'7'},'agent-1')['error_code'],'INVALID_ARGUMENT')
        restored=load_native().World.restore(world.checkpoint());self.assertEqual(restored.snapshot()['event_counts'],world.snapshot()['event_counts'])
        self.assertEqual(restored.snapshot()['event_counts']['tick'],7)
        restored.check_invariants()
