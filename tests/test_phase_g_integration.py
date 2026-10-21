from contextlib import closing
from pathlib import Path
import tempfile
import unittest

from underworld import storage,stabilization as stable,planning,runtime,knowledge,care,memory,enclosure,teaching
from underworld.config import load
from test_phase_f_knowledge import injection

ROOT=Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'world.sqlite'
        self.config=load(ROOT/'config/living-world-g.toml')
        self.config['world'].update(population=1,width_m=16,height_m=16)
        self.config['execution'].update(epoch_ticks=10,batch_ticks=5,checkpoint_keep=2,metrics_keep=16,memory_recent=4)
        stable.initialize(self.path,self.config,call_limit=0,knowledge_profile={'profile':'woodcraft','recipient':'agent-1'})

    def finish(self,ticks=300):
        for _ in range(ticks):
            stable.step(self.path)
            task=stable.status(self.path).get('tasks',{})
            if not task.get('active'):return task['history'][-1]
        self.fail('bounded task did not finish')

    def test_pending_native_request_reconciles_after_rotation(self):
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})
        stable.step(self.path);before=stable.status(self.path);pending=before['pending']
        self.assertTrue(pending)
        runtime.rotate(self.path)
        self.assertEqual(stable.status(self.path),before)
        result=self.finish();self.assertEqual(result['outcome'],'completed',result)
        with closing(storage._connect(self.path,readonly=True)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM decisions WHERE json_extract(request,'$.request_id')=?",(pending['request_id'],)).fetchone()[0],1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])
        self.assertTrue(runtime.verify_archives(self.path)['verified_retained'])

    def test_sources_and_procedure_reuse_survive_pruning(self):
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})
        result=self.finish();ident=result['procedure_episode_id']
        teaching.intervene(self.path,injection(self.path,care.text()))
        initial=knowledge.view(self.path,'agent-1')
        with closing(storage._connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE')
            for i in range(25):memory.episode(db,'agent-1','old:'+str(i),0,'action_result',{'text':str(i)})
            for i in range(30):stable._event(db,'agent-1',0,'audit_fixture',{'n':i})
            memory.seal(db);db.commit()
        runtime.rotate(self.path)
        self.assertEqual(knowledge.view(self.path,'agent-1'),initial)
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})
        self.assertEqual(stable.status(self.path)['tasks']['active']['procedure_source'],ident)
        self.assertEqual(self.finish()['outcome'],'completed')
        with closing(storage._connect(self.path,readonly=True)) as db:
            stable.verify_event_chain(db)
            meta=storage.loads(db.execute('SELECT payload FROM stabilization_meta').fetchone()[0])
            self.assertGreater(meta['archived_event_count'],0)
            self.assertTrue(meta['event_chain_anchor'])
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_unsubmitted_reservation_refuses_rotation(self):
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})
        def crash(stage):
            if stage=='after_reservations':raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):stable.step(self.path,fault=crash)
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'unsubmitted'):runtime.rotate(self.path)
        self.assertEqual(before,self.path.read_bytes())
        self.assertEqual(self.finish()['outcome'],'completed')

    def test_publication_and_transaction_interruptions_retry(self):
        for stage in ('after_checkpoint','rotation_before_commit'):
            def crash(point,tick):
                if point==stage:raise RuntimeError(point)
            with self.assertRaises(RuntimeError):runtime.rotate(self.path,fault=crash)
            epoch=runtime.status(self.path)['epoch']
            runtime.rotate(self.path)
            self.assertEqual(runtime.status(self.path)['epoch'],epoch+1)
            self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_same_native_head_changed_knowledge_cannot_reuse_backup(self):
        def crash(stage,tick):
            if stage=='after_checkpoint':raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):runtime.rotate(self.path,fault=crash)
        before=storage.inspect(self.path)['state_hash']
        teaching.intervene(self.path,injection(self.path,care.text()))
        self.assertEqual(storage.inspect(self.path)['state_hash'],before)
        with self.assertRaisesRegex(ValueError,'cognitive/controller'):runtime.rotate(self.path)

    def test_quota_never_deletes_last_valid_archive(self):
        runtime.rotate(self.path);directory=Path(str(self.path)+'.epochs')
        existing={p.name:p.read_bytes() for p in directory.iterdir()}
        before=storage.inspect(self.path)['state_hash']
        with self.assertRaisesRegex(ValueError,'quota'):runtime.rotate(self.path,self.config['execution']|{'max_archive_bytes':1})
        self.assertEqual({p.name:p.read_bytes() for p in directory.iterdir()},existing)
        self.assertEqual(storage.inspect(self.path)['state_hash'],before)

    def test_missing_or_corrupt_retained_archive_stops_run_before_ticks(self):
        runtime.rotate(self.path);file=next(Path(str(self.path)+'.epochs').glob('*.sqlite'))
        original=file.read_bytes();before=storage.inspect(self.path)['tick']
        file.write_bytes(original+b'corrupt')
        with self.assertRaisesRegex(ValueError,'checksum'):stable.run(self.path,1,10)
        self.assertEqual(storage.inspect(self.path)['tick'],before)
        file.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):stable.run(self.path,1,10)
        self.assertEqual(storage.inspect(self.path)['tick'],before)

    def test_care_claim_access_and_real_native_false_lesson(self):
        teaching.intervene(self.path,injection(self.path,care.text('water')))
        ident=knowledge.view(self.path,'agent-1')['records'][0]['episode_id']
        planning.assign(self.path,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':ident})
        result=self.finish(600)
        self.assertEqual(result['outcome'],'blocked',result)
        tests=[r for r in knowledge.view(self.path,'agent-1')['records'] if r['kind']=='knowledge_test']
        self.assertTrue(tests)
        self.assertEqual(tests[0]['status'],'rejected')
        self.assertEqual(tests[0]['error_code'],'INVALID_ARGUMENT')
        runtime.rotate(self.path)
        self.assertEqual(knowledge.view(self.path,'agent-1')['counts']['knowledge_test'],1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_true_care_claim_changes_actual_native_reserve(self):
        before=storage.inspect(self.path)['state_hash']
        teaching.intervene(self.path,injection(self.path,care.text()))
        self.assertEqual(storage.inspect(self.path)['state_hash'],before)
        ident=knowledge.view(self.path,'agent-1')['records'][0]['episode_id']
        planning.assign(self.path,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':ident})
        result=self.finish()
        self.assertEqual(result['outcome'],'completed',result)
        self.assertTrue(result['executor_goal_credit'])
        self.assertEqual(result['lesson_episode_id'],ident)
        self.assertEqual(knowledge.view(self.path,'agent-1')['counts']['knowledge_test'],1)
        self.assertEqual(knowledge.view(self.path,'agent-1')['records'][0]['status'],'completed')

    def test_foreign_lesson_and_arbitrary_prose_refused(self):
        teaching.intervene(self.path,injection(self.path,'Feed everything with magic'))
        ident=knowledge.view(self.path,'agent-1')['records'][0]['episode_id']
        with self.assertRaisesRegex(ValueError,'bounded care'):planning.assign(self.path,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':ident})
        with self.assertRaisesRegex(ValueError,'own accessed'):planning.assign(self.path,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':999})

    def test_pen_rejects_absent_center_and_out_of_bounds(self):
        for params in ({},{'position_m':[1,1]}):
            planning.assign(self.path,'agent-1','build_pen',params)
            row=self.finish()
            self.assertEqual(row['outcome'],'blocked',row)
        self.assertFalse(any(x['kind']=='fence' for x in storage.inspect(self.path)['entities']))

    def test_legacy_supervisor_cannot_replace_controller(self):
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'living-world run'):runtime.run(self.path,1,10,require_isolation=False)
        self.assertEqual(before,self.path.read_bytes())

    def test_remembered_route_never_gathers_from_stale_location(self):
        obs=storage.observe(self.path,['agent-1'])[0]
        remembered={'old':{'entity_id':'old','kind':'food','position_m':[5,3],'radius_m':0,'last_seen_tick':0}}
        choice=planning.remembered_route(obs,remembered,('food',))
        self.assertEqual(choice['action'],'move')
        self.assertTrue(choice['source'].startswith('own_remembered_source'))
        remembered['old']['position_m']=list(obs['own_state']['position_m'])
        self.assertIsNone(planning.remembered_route(obs,remembered,('food',)))
        self.assertEqual(remembered,{})

    def test_portable_bundle_includes_verified_retained_epochs(self):
        runtime.rotate(self.path)
        output=Path(self.tmp.name)/'portable.sqlite'
        result=runtime.backup(self.path,'portable',output)
        self.assertEqual(result['archive_files'],1)
        self.assertEqual(runtime.verify_archives(output)['verified_retained'],1)
        self.assertEqual(storage.inspect(self.path)['state_hash'],storage.inspect(output)['state_hash'])
        self.assertEqual(stable.run(output,1,15)['status'],'target_reached')
        self.assertTrue(storage.replay(output)['replay_matches'])

    def test_builder_moves_clear_of_unbuilt_footprint(self):
        o=storage.observe(self.path,['agent-1'])[0]
        point=list(o['own_state']['position_m'])
        choice,ready=planning.placement_stance(o,point,'explicit_site')
        self.assertFalse(ready);self.assertEqual(choice['action'],'move')
        import math
        self.assertGreaterEqual(math.dist([choice['params']['x_m'],choice['params']['y_m']],point),.8)

    def test_active_care_lesson_ablation_refuses_use(self):
        teaching.intervene(self.path,injection(self.path,care.text()))
        ident=knowledge.view(self.path,'agent-1')['records'][0]['episode_id']
        planning.assign(self.path,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':ident})
        # Pure compiler gate under an explicitly disabled observation context;
        # native body/resources remain untouched.
        with closing(storage._connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE');world,cfg,_,_=storage._head(db);cfg['execution']['episodic_memory']=False
            s=stable._load(db,'agent-1')
            self.assertIsNone(stable._task_request(db,s,world.observe_batch(['agent-1'])[0],cfg,None))
            self.assertEqual(s['tasks']['history'][-1]['reason'],'care_lesson_access_disabled')
            db.rollback()

    def test_desktop_checks_model_tasks_on_nondefault_inhabitant(self):
        from underworld.app import validate_model_off
        other=Path(self.tmp.name)/'two-people.sqlite';cfg=load(ROOT/'config/living-world-g.toml');cfg['world']['population']=2
        stable.initialize(other,cfg,call_limit=0)
        planning.assign(other,'agent-2','inspect_problem',{'target':'resource-1'},mode='model_assisted')
        before=other.read_bytes()
        with self.assertRaisesRegex(ValueError,'model-off'):validate_model_off(other)
        self.assertEqual(before,other.read_bytes())

    def test_crash_after_rotation_commit_keeps_verified_recovery_points(self):
        runtime.rotate(self.path);runtime.rotate(self.path)
        def crash(stage,tick):
            if stage=='rotation_after_commit':raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):runtime.rotate(self.path,fault=crash)
        self.assertEqual(runtime.verify_archives(self.path)['epoch'],3)
        runtime.rotate(self.path)
        self.assertEqual(len(list(Path(str(self.path)+'.epochs').glob('*.sqlite'))),2)
        self.assertTrue(storage.replay(self.path)['replay_matches'])


class PenGeometryTests(unittest.TestCase):
    def test_native_stock_behind_stump_is_approached_and_collected(self):
        import shlex
        from ecology_fixtures import render
        from underworld.native import load_native
        from test_phase6 import act
        w=load_native().World(seed=21,population=1,width=16,height=16,dt=.2,bodies=True,scripted=False)
        lines=w.checkpoint().splitlines();n=int(lines[3]);rows=[shlex.split(x) for x in lines[4:4+n]]
        template=list(next(x for x in rows if x[0]=='resource-4'))
        for row in rows:
            if row[0]=='agent-1':row[2:4]=['12','4']
            if row[0]=='tree-2':row[5]=row[16]='800000000';row[14]='stump';row[15]='.1'
        # NEW fixture: retained tree stump + finite products exactly replace8kg.
        for ident,kind,pos,mass in [('empty-a','wood',(15.2,2),0),('empty-b','wood',(14,.8),0),
                                    ('fiber-stock','fiber',(14.9,2.9),800000000),('wood-stock','wood',(14.9,1.1),6400000000)]:
            row=list(template);row[0:6]=[ident,kind,str(pos[0]),str(pos[1]),'.15',str(mass)];rows.append(row)
        lines[3]=str(len(rows));lines[4:4+n]=list(map(render,rows));w=load_native().World.restore('\n'.join(lines)+'\n');w.check_invariants()
        known={'wood-stock':{'entity_id':'wood-stock','kind':'wood','position_m':[14.9,1.1],'radius_m':.15}}
        navigation={};completed=False
        for _ in range(40):
            o=w.observe_batch(['agent-1'])[0];o['_route_memory']=navigation
            fresh=next((x for x in o['visible_entities'] if x['entity_id']=='wood-stock'),None)
            if fresh:choice=planning._approach(o,fresh,planning._option('collect_wood',{'material':'wood','mass_kg':.1},'wood-stock'))
            else:choice=planning.remembered_route(o,known,('wood',),navigation)
            self.assertIsNotNone(choice,'perceived route must make progress')
            result=act(w,choice['action'],[choice['target']] if choice.get('target') else [],choice['params'],seconds=choice['duration'])
            self.assertEqual(result['status'],'completed',result)
            if choice['action']=='collect_wood':completed=True;break
        self.assertTrue(completed,'approach endpoint must persist rather than circle the stump')
        self.assertEqual(w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug']['wood'],'100000000')

    def test_blueprint_has_closed_native_barrier_and_one_gate(self):
        from ecology_fixtures import world,layout
        from test_phase6 import act
        points=enclosure.blueprint([9,9])[1:]
        self.assertEqual(len(points),12)
        self.assertEqual(sum(x[0]=='gate' for x in points),1)
        w=layout(world(),positions={'agent-1':(9,9),'animal-1':(8.5,9),'animal-2':(9.5,9)},structures=points)
        result=act(w,'move',params={'x_m':9,'y_m':5},seconds=5)
        self.assertEqual(result['error_code'],'COLLISION')
        w.step(300);w.check_invariants()
        for entity in w.snapshot()['entities']:
            if entity['kind']=='animal':
                self.assertTrue(7.2<entity['position_m'][0]<10.8)
                self.assertTrue(7.2<entity['position_m'][1]<10.8)


if __name__=='__main__':unittest.main()
