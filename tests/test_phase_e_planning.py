from contextlib import closing
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from planning_fixtures import create,until_done,collision_layout
from ecology_fixtures import balances,render
from underworld import storage,stabilization as stable,planning
from underworld.native import load_native
from underworld.workshop import AssignedProcedure


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'world.sqlite'
    def tearDown(self):self.tmp.cleanup()
    def own(self):return storage.observe(self.path,['agent-1'])[0]['own_state']

    def test_harvest_craft_planks_trough_and_real_water_delivery(self):
        create(self.path)
        for goal in ('craft_tool','make_planks','build_trough','provide_water'):
            planning.assign(self.path,'agent-1',goal);row=until_done(self.path)
            self.assertEqual(row['outcome'],'completed',row)
            self.assertTrue(row['evidence'])
        snapshot=storage.inspect(self.path)
        trough=next(x for x in snapshot['entities'] if x['kind']=='trough')
        self.assertEqual(int(trough['inventory_ug']['water']),300000000)
        self.assertGreater(self.own()['workmanship'],0)
        self.assertTrue(storage.replay(self.path)['replay_matches'])
        with closing(storage._connect(self.path,readonly=True)) as db:memory_rows=db.execute("SELECT agent,payload FROM episodes WHERE kind='verified_procedure'").fetchall()
        self.assertEqual(len(memory_rows),4);self.assertEqual({r[0] for r in memory_rows},{'agent-1'})
        self.assertTrue(all(json.loads(r[1])['skill_granted'] is False for r in memory_rows))

    def test_inflight_task_backup_memory_scheduler_and_replay(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool')
        stable.step(self.path);self.assertEqual(stable.status(self.path)['pending_owner'],'task')
        backup=Path(self.tmp.name)/'saved.sqlite';storage.save(self.path,'task-mid-action',backup)
        until_done(self.path);until_done(backup)
        self.assertEqual(storage.inspect(self.path)['state_hash'],storage.inspect(backup)['state_hash'])
        self.assertEqual(stable.status(self.path),stable.status(backup))
        self.assertEqual(storage.mind(self.path,'agent-1'),storage.mind(backup,'agent-1'))
        self.assertTrue(storage.replay(backup)['replay_matches'])

    def test_crash_after_native_commit_reconciles_one_task_action(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool')
        def crash(stage):
            if stage=='after_native_commit':raise RuntimeError('interruption')
        with self.assertRaises(RuntimeError):stable.step(self.path,fault=crash)
        self.assertEqual(until_done(self.path)['outcome'],'completed')
        self.assertEqual(len(self.own()['tools']),1)
        self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_urgent_need_preempts_without_counting_task_completion(self):
        create(self.path);storage.advance(self.path,160)
        planning.assign(self.path,'agent-1','craft_tool');stable.step(self.path)
        s=stable.status(self.path)
        self.assertIsNotNone(s['goal']);self.assertEqual(s['tasks']['active']['steps'],0)
        self.assertEqual(s['pending_owner'],'survival')

    def test_unsupported_absent_and_private_procedure_reuse(self):
        create(self.path)
        for goal,params,reason in (('teach_procedure',{},'unsupported_task'),('inspect_problem',{'target':'foreign-hidden'},'not_observed')):
            planning.assign(self.path,'agent-1',goal,params);r=until_done(self.path)
            self.assertEqual(r['outcome'],'blocked');self.assertIn(reason,r['reason'])
        self.assertFalse(stable.status(self.path)['tasks']['procedures'])
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'});self.assertEqual(until_done(self.path)['outcome'],'completed')
        planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})
        task=stable.status(self.path)['tasks']['active']
        self.assertEqual(task['origin'],'own_verified_procedure_reuse');self.assertIsInstance(task['procedure_source'],int)
        with self.assertRaises(ValueError):planning.assign(self.path,'agent-2','rest')
        with self.assertRaises(ValueError):planning.assign(self.path,'agent-1','rest')

    def test_observed_empty_supply_is_bounded_and_not_consumed(self):
        create(self.path,ecology=True)
        # Resources here are deliberately absent from a copied permitted view;
        # only pure selection is tested, with no state or stock injection.
        planning.assign(self.path,'agent-1','obtain_wood')
        s=stable.status(self.path);o=storage.observe(self.path,['agent-1'])[0]
        o['visible_entities']=[]
        for _ in range(13):options,done,reason=planning.choices(s['tasks'],o)
        self.assertFalse(done);self.assertIn('no_observed_accessible',reason)
        self.assertFalse(options);self.assertLessEqual(s['tasks']['active']['search'],4)

    def test_own_verified_failure_changes_source_choice_under_memory_ablation(self):
        create(self.path);planning.assign(self.path,'agent-1','obtain_wood')
        s=stable.status(self.path);o=storage.observe(self.path,['agent-1'])[0]
        # Selection-only matched local observations; no world snapshot/registry.
        o['visible_entities']=[dict(entity_id='wood-a',kind='wood',mass_ug='500000000',position_m=[2.6,2.3],radius_m=.15),
                               dict(entity_id='wood-b',kind='wood',mass_ug='500000000',position_m=[2.6,2.8],radius_m=.15)]
        o['own_state']['position_m']=[2,2.3]
        e=s['tasks'];t=e['active'];first=planning.choices(e,o)[0][0]
        t['pending_choice']=first
        # This handler receives only journal-verified receipts in production.
        # Native receipt behavior itself is covered by the durable crash tests.
        planning.record(s,dict(action_type='collect_wood',request_id='own-native-failure',target_ids=['wood-a']),
                        dict(status='failed',error_code='INSUFFICIENT_RESOURCE',event_refs=['7'],observable_effects={}),o)
        adaptive=planning.choices(e,o)[0][0]
        control=copy.deepcopy(e);control['active']['mode']='episodic_only'
        episodic=planning.choices(control,o)[0][0]
        self.assertEqual(first['target'],'wood-a');self.assertEqual(adaptive['target'],'wood-b');self.assertEqual(episodic['target'],'wood-a')
        self.assertEqual(e['beliefs']['wood:wood-a']['evidence'],['own-native-failure'])

    def test_invalid_parameters_and_cancel_inflight_are_rejected(self):
        create(self.path)
        with self.assertRaises(ValueError):planning.assign(self.path,'agent-1','obtain_food',{'mass_kg':True})
        with self.assertRaises(ValueError):planning.assign(self.path,'agent-1','rest',{'invented':1})
        planning.assign(self.path,'agent-1','craft_tool');stable.step(self.path)
        self.assertTrue(planning.cancel(self.path,'agent-1')['active']['cancel_requested'])
        self.assertEqual(until_done(self.path)['outcome'],'blocked')

    def test_broken_tool_replans_from_actual_native_scrap(self):
        # Declared aged-tool test fixture: durability is one at test start.
        import shlex
        h=AssignedProcedure();tool=h.plank_stock()
        # plank_stock already spent two uses; arrange one remaining use before
        # an actual native craft breaks it. No mass/stock is changed by aging.
        lines=h.world.checkpoint().splitlines();n=int(lines[3])
        for i in range(4,4+n):
            row=shlex.split(lines[i])
            if row[0]==tool:
                row[20+2*int(row[6])]='1';lines[i]=render(row)
        w=load_native().World.restore('\n'.join(lines)+'\n');h=AssignedProcedure(world=w)
        # Existing planks/offcuts are deposited in a real box to free capacity.
        h.act('begin_construction',params={'recipe_id':'storage_box','x_m':6.7,'y_m':4.3})
        box=h.entity('construction')['entity_id'];h.act('work_construction',[box],duration=8)
        h.act('store_item',[box],{'material':'wood_offcut','mass_kg':.2})
        pile=next(x for x in h.observe()['visible_entities'] if x['kind']=='wood' and int(x['mass_ug'])>=1000000000)
        h.act('collect_wood',[pile['entity_id']],{'material':'wood','mass_kg':1});h.act('craft',params={'recipe_id':'planks','tool_id':tool},duration=3)
        self.assertFalse(h.observe()['own_state']['tools'])
        o=h.observe();s=dict(tasks={'beliefs':{},'active':dict(goal='craft_tool',params={},mode='adaptive',created_tick=int(o['tick']),steps=0,failures=0,search=0)})
        choices,done,reason=planning.choices(s['tasks'],o)
        self.assertFalse(done);self.assertIsNone(reason);self.assertEqual(choices[0]['action'],'craft')
        h.act('craft',params=choices[0]['params'],duration=choices[0]['duration'])
        self.assertTrue(h.observe()['own_state']['tools']);h.world.check_invariants()

    def test_animal_thirst_care_uses_real_native_reports_and_transfer(self):
        create(self.path,care=True);storage.advance(self.path,400)
        planning.assign(self.path,'agent-1','tend_animal',{'target':'animal-1'})
        row=until_done(self.path)
        self.assertEqual(row['outcome'],'completed',row)
        self.assertGreater(row['delivered_ug'],0)
        with closing(storage._connect(self.path,readonly=True)) as db:
            w,_,_,_=storage._head(db);self.assertEqual(set(balances(w).values()),{0})

    def test_model_invalid_choice_falls_back_and_reservation_remains_bounded(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool',mode='model_assisted')
        with patch('underworld.cognition.bounded_call',return_value=('{"choice":999,"reason":"invalid fixture"}',{'model':'mock-only'},.01)) as call:
            row=until_done(self.path)
        self.assertEqual(row['outcome'],'completed');self.assertEqual(call.call_count,1)
        self.assertEqual(stable.status(self.path)['tasks']['calls'],1)
        with closing(storage._connect(self.path,readonly=True)) as db:
            events=[json.loads(r[0]) for r in db.execute('SELECT payload FROM stabilization_events')]
        replies=[r['data'] for r in events if r['kind']=='task_inference_result']
        self.assertEqual(replies[0]['origin'],'deterministic_fallback')

    def test_actual_collision_receipt_changes_later_choice_in_matched_branches(self):
        from underworld.lab_policy import Driver
        collision_layout(self.path)
        planning.assign(self.path,'agent-1','obtain_wood');stable.step(self.path)
        self.assertEqual(stable.status(self.path)['tasks']['active']['pending_choice']['source'],'wood:wood-a')
        # Native moving peer enters the previously clear approach, causing a
        # real collision. Cancellation waits for that actual terminal receipt.
        planning.cancel(self.path,'agent-1')
        Driver(self.path,'agent-2').act('move',parameters={'x_m':3.7,'y_m':3},seconds=1.2)
        row=until_done(self.path)
        self.assertEqual(row['outcome'],'blocked')
        e=stable.status(self.path)['tasks'];self.assertEqual(e['beliefs']['wood:wood-a']['last_error'],'COLLISION')
        Driver(self.path,'agent-2').act('move',parameters={'x_m':4,'y_m':2},seconds=1.2)
        other=Path(self.tmp.name)/'episodic.sqlite';storage.save(self.path,'matched-memory-ablation',other)
        selected=[]
        for path,mode in ((self.path,'adaptive'),(other,'episodic_only')):
            planning.assign(path,'agent-1','obtain_wood',mode=mode);stable.step(path)
            selected.append(stable.status(path)['tasks']['active']['pending_choice']['source'])
            self.assertEqual(until_done(path)['outcome'],'completed')
            self.assertTrue(storage.replay(path)['replay_matches'])
        self.assertEqual(selected,['wood:wood-b','wood:wood-a'])

    def test_already_satisfied_goal_does_not_fabricate_new_procedure_credit(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool');until_done(self.path)
        previous=stable.status(self.path)['tasks']['procedures']['craft_tool']['successes']
        planning.assign(self.path,'agent-1','craft_tool');row=until_done(self.path)
        self.assertFalse(row['executor_goal_credit']);self.assertFalse(row['evidence'])
        self.assertEqual(stable.status(self.path)['tasks']['procedures']['craft_tool']['successes'],previous)

    def test_missing_procedure_source_fails_closed(self):
        from underworld import memory
        create(self.path);planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'});until_done(self.path)
        episode=stable.status(self.path)['tasks']['procedures']['inspect_problem']['episode_id']
        with closing(storage._connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM episodes WHERE id=?',(episode,));memory.seal(db);db.commit()
        with self.assertRaisesRegex(ValueError,'evidence unavailable'):planning.assign(self.path,'agent-1','inspect_problem',{'target':'resource-1'})

    def test_task_deadline_also_applies_while_survival_is_urgent(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool')
        storage.advance(self.path,730);stable.step(self.path)
        e=stable.status(self.path)['tasks'];self.assertIsNone(e['active'])
        self.assertIn('deadline',e['history'][-1]['reason']);self.assertEqual(e['history'][-1]['outcome'],'blocked')

    def test_model_reservation_survives_interruption_without_extra_call(self):
        create(self.path);planning.assign(self.path,'agent-1','craft_tool',mode='model_assisted')
        with patch('underworld.cognition.bounded_call',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):stable.step(self.path)
        self.assertEqual(stable.status(self.path)['tasks']['calls'],1)
        with patch('underworld.cognition.bounded_call',side_effect=AssertionError('reservation cannot be retried')):
            self.assertEqual(until_done(self.path)['outcome'],'completed')

    def test_desktop_model_off_boundary_rejects_model_assisted_task(self):
        import io
        from contextlib import redirect_stderr
        from underworld.app import main
        create(self.path);planning.assign(self.path,'agent-1','craft_tool',mode='model_assisted')
        before=storage.inspect(self.path)['state_hash']
        with redirect_stderr(io.StringIO()),patch('underworld.cognition.bounded_call',side_effect=AssertionError('desktop must not call model')):
            with self.assertRaises(SystemExit) as exited:main(['--db',str(self.path),'--seconds','1','--port','0','--no-browser','--exit-after-run'])
        self.assertEqual(exited.exception.code,2)
        self.assertEqual(storage.inspect(self.path)['state_hash'],before)

    def test_utility_reference_policy_really_runs(self):
        create(self.path,managed=False,utility=True)
        with closing(storage._connect(self.path,readonly=True)) as db:
            _,_,metadata,_=storage._head(db);self.assertEqual(metadata['policy'],'utility')
        storage.advance(self.path,30)
        self.assertGreater(storage.inspect(self.path)['recorded_decisions'],0)

    def test_animal_warmup_is_matched_before_any_policy_acts(self):
        other=Path(self.tmp.name)/'utility.sqlite'
        create(self.path,care=True,neutral_warmup_ticks=400)
        create(other,care=True,neutral_warmup_ticks=400,managed=False,utility=True)
        checkpoints=[]
        for path in (self.path,other):
            with closing(storage._connect(path,readonly=True)) as db:
                w,_,_,_=storage._head(db);checkpoints.append(w.checkpoint())
            self.assertEqual(storage.inspect(path)['tick'],'400')
            self.assertEqual(storage.inspect(path)['recorded_decisions'],0)
        self.assertEqual(checkpoints[0],checkpoints[1])
