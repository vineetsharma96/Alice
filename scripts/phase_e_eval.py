"""Bounded E task comparison, with raw native/SQLite evidence in NEW directories."""
import argparse
from contextlib import closing,ExitStack
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from planning_fixtures import create,collision_layout,until_done
from underworld import storage,stabilization as stable,planning
from underworld.lab_policy import Driver
from underworld.planning_model import PlanningModel
from ecology_fixtures import balances
from stabilization_common import model_server


CASES=('harvest_craft','water_delivery','depleted_forage','blocked_site','animal_thirst','absent_peer')
ARMS=('utility','authored','episodic_only','adaptive','model_assisted')


def evidence(path):
    with closing(storage._connect(path,readonly=True)) as db:
        w,_,metadata,_=storage._head(db);w.check_invariants()
        decisions=[dict(tick=tick,request=json.loads(req),submission=json.loads(result)) for tick,req,result in db.execute('SELECT tick,request,result FROM decisions ORDER BY id')]
        terminal=[json.loads(r[0]) for r in db.execute("SELECT payload FROM episodes WHERE agent='agent-1' AND kind='action_result' ORDER BY id")]
        control=[json.loads(r[0]) for r in db.execute('SELECT payload FROM stabilization_events ORDER BY id')] if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_events'").fetchone() else []
        return dict(decisions=decisions,terminal=terminal,controller_events=control,balances=balances(w),active_policy=metadata['policy'])


def run_case(folder,seed,case,arm,provider=None):
    path=folder/'run.sqlite';positions={'agent-1':(2.5,3)} if seed in (929,1329) else {'agent-1':(1.5,3.2),'resource-2':(3.3,2.5)} if seed in (1049,1449) else {}
    goal,params={'harvest_craft':('craft_tool',{}),'water_delivery':('provide_water',{'target':'fixture-0'}),
                 'depleted_forage':('obtain_food',{}),'blocked_site':('build_trough',{'position_m':[4,4]}),
                 'animal_thirst':('tend_animal',{'target':'animal-1'}),'absent_peer':('inspect_problem',{'target':'absent-peer'})}[case]
    start=time.perf_counter()
    create(path,seed=seed,ecology=case=='depleted_forage',scarce=case=='depleted_forage',
           positions=positions,structures=[('trough',1.5,4.4)] if case=='water_delivery' else (),care=case=='animal_thirst',managed=arm!='utility',utility=arm=='utility',neutral_warmup_ticks=400 if case=='animal_thirst' else 0)
    initial=storage.inspect(path);setup_wall=time.perf_counter()-start
    with closing(storage._connect(path,readonly=True)) as db:
        world,_,_,_=storage._head(db);initial_native_hash=storage.digest(world.checkpoint())
    start=time.perf_counter();history=None
    if arm=='utility':
        storage.advance(path,round(60/initial['dt_s']));state=None
    else:
        planning.assign(path,'agent-1',goal,params,arm)
        for _ in range(round(60/initial['dt_s'])):
            stable.step(path,provider=provider);state=stable.status(path)
            if not state['tasks']['active']:
                history=state['tasks']['history'][-1];break
            if time.perf_counter()-start>180:break
        if history is None:history=dict(outcome='unfinished',reason='evaluation_simulated_or_wall_horizon',active_task=state['tasks']['active'])
    wall=time.perf_counter()-start;final=storage.inspect(path);raw=evidence(path)
    (folder/'receipts.json').write_text(json.dumps(raw,indent=2)+'\n')
    replay=storage.replay(path)
    terminal=raw['terminal'];request_by_id={r['request']['request_id']:r['request'] for r in raw['decisions']}
    actual_transfers=sum(round(request_by_id[r['request_id']]['parameters'].get('mass_kg',0)*1e9)
                         for r in terminal if r['status']=='completed' and r['request_id'] in request_by_id)
    errors=[dict(request_id=r['request_id'],status=r['status'],error=r['error_code']) for r in terminal if r['status']!='completed']
    own=storage.observe(path,['agent-1'])[0]['own_state']
    return dict(seed=seed,case=case,arm=arm,goal=goal,history=history,active_policy=raw['active_policy'],baseline_assignment_interface=arm!='utility',evaluation_horizon_s=60,
                goal_completed=bool(history and history['outcome']=='completed'),initial_native_hash=initial_native_hash,setup_wall_s=setup_wall,wall_s=wall,
                simulated_s=(int(final['tick'])-int(initial['tick']))*final['dt_s'],initial_tick=initial['tick'],final_tick=final['tick'],
                submitted=len(raw['decisions']),accepted=sum(r['submission']['status']=='accepted' for r in raw['decisions']),
                completed=sum(r['status']=='completed' for r in terminal),errors=errors,alive=own['alive'],
                actual_transfer_requests_ug=actual_transfers,initial_material_totals_ug=initial['material_totals_ug'],
                final_material_totals_ug=final['material_totals_ug'],boundary_sources_ug=final['boundary_sources_ug'],balances=raw['balances'],
                model_calls=state['tasks']['calls'] if state else 0,model_latency_s=state['tasks']['model_latency_s'] if state else 0,
                operator_selections=[r['data']['choice']['choice_origin'] for r in raw['controller_events'] if r['kind']=='task_operator_selected'],
                inference=[r['data'] for r in raw['controller_events'] if r['kind']=='task_inference_result'],replay=replay,state_hash=final['state_hash'])


def adaptation(folder,seed):
    p=folder/'adaptive.sqlite';collision_layout(p,seed)
    planning.assign(p,'agent-1','obtain_wood');stable.step(p);planning.cancel(p,'agent-1')
    Driver(p,'agent-2').act('move',parameters={'x_m':3.7,'y_m':3},seconds=1.2)
    first=until_done(p);Driver(p,'agent-2').act('move',parameters={'x_m':4,'y_m':2},seconds=1.2)
    control=folder/'episodic.sqlite';storage.save(p,'matched-experience-ablation',control)
    rows=[]
    for path,mode in ((p,'adaptive'),(control,'episodic_only')):
        start=time.perf_counter();initial=storage.inspect(path)
        planning.assign(path,'agent-1','obtain_wood',mode=mode);stable.step(path)
        choice=stable.status(path)['tasks']['active']['pending_choice']
        result=until_done(path);final=storage.inspect(path);raw=evidence(path)
        (folder/f'{mode}-receipts.json').write_text(json.dumps(raw,indent=2)+'\n')
        rows.append(dict(mode=mode,choice=choice,result=result,wall_s=time.perf_counter()-start,
                         simulated_s=(int(final['tick'])-int(initial['tick']))*final['dt_s'],replay=storage.replay(path),balances=raw['balances']))
    return dict(seed=seed,source_failure=first,rows=rows,
                passed=rows[0]['choice']['source']=='wood:wood-b' and rows[1]['choice']['source']=='wood:wood-a' and
                all(r['result']['outcome']=='completed' and r['replay']['replay_matches'] and not any(r['balances'].values()) for r in rows))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--split',choices=['development','confirmation'],required=True)
    parser.add_argument('--local-model',action='store_true');parser.add_argument('--cases',nargs='+',choices=CASES,default=CASES)
    parser.add_argument('--arms',nargs='+',choices=ARMS,default=ARMS[:-1])
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    seeds=(21,31) if args.split=='development' else (1329,1449)
    report=dict(protocol_sha256=hashlib.sha256((ROOT/'docs/PHASE_E_PLANNING.md').read_bytes()).hexdigest(),
                controller_source_id=stable.source_id(),split=args.split,seeds=seeds,runs=[],adaptation=[])
    def save():args.evidence.parent.mkdir(parents=True,exist_ok=True);args.evidence.write_text(json.dumps(report,indent=2)+'\n')
    with ExitStack() as stack:
        provider=None
        if args.local_model:provider=PlanningModel(stack.enter_context(model_server(args.output/'model',port=8082)))
        for seed in seeds:
            for case in args.cases:
                for arm in args.arms:
                    if arm=='model_assisted' and not provider:raise ValueError('real model arm requires --local-model')
                    folder=args.output/f'{seed}-{case}-{arm}';folder.mkdir()
                    row=run_case(folder,seed,case,arm,provider);report['runs'].append(row);save()
                    print(json.dumps({k:row[k] for k in ('seed','case','arm','goal_completed','simulated_s','wall_s','model_calls','errors')}),flush=True)
            folder=args.output/f'{seed}-adaptation';folder.mkdir();report['adaptation'].append(adaptation(folder,seed));save()
    report['gates']=dict(utility_baseline_active=all(r['active_policy']=='utility' and r['submitted']>0 for r in report['runs'] if r['arm']=='utility'),
                         matched_initial_physics=all(len({r['initial_native_hash'] for r in report['runs'] if r['seed']==seed and r['case']==case})==1 for seed in seeds for case in args.cases),
                         native_integrity=all(not any(r['balances'].values()) and r['replay']['replay_matches'] for r in report['runs']),
                         feasible_production=all(r['goal_completed'] for r in report['runs'] if r['arm']!='utility' and r['case'] in ('harvest_craft','water_delivery')),
                         scarcity_not_claimed=all(not r['goal_completed'] for r in report['runs'] if r['case'] in ('depleted_forage','blocked_site','absent_peer')),
                         experience_changes_choice=all(r['passed'] for r in report['adaptation']))
    report['passed']=all(report['gates'].values());save();print(json.dumps({'passed':report['passed'],'gates':report['gates']}))
    return 0 if report['passed'] else 1


if __name__=='__main__':sys.exit(main())
