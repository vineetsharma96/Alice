"""Fixed development/held-out benchmarks; every setup/change is a native action."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import storage,cognition,stabilization as stable
from underworld.policy import choose
from underworld.lab_policy import Driver
from underworld.wire import dumps
from stabilization_common import create,clone,read,write,model_server

ARMS=('utility','legacy_model','stable_authored','stable_model')
SCENARIOS=('carried','gather','unavailable','depleted','interrupted')


def fixture(path,seed,scenario,dev=False):
    create(path,seed,food=0 if scenario=='unavailable' else .4 if scenario=='depleted' else .8 if dev else .6,
           water=1.2 if dev else 1.8,age=160)
    driver=Driver(path,'agent-1')
    if scenario=='carried':driver.act('gather',['resource-1'],{'mass_kg':.2})
    if scenario in ('gather','depleted'):driver.navigate((6,2))
    return path


def init_samples(path,arm):
    o=storage.observe(path,['agent-1'])[0]
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE evaluation_control(payload TEXT)')
        db.execute('CREATE TABLE evaluation_samples(tick INTEGER PRIMARY KEY,payload TEXT)')
        db.execute('INSERT INTO evaluation_control VALUES(?)',(dumps(dict(start_tick=int(o['tick']),arm=arm,navigation={},offset=0)),))
        db.commit()
    return o


def advance(path,count,endpoint=None,competition=False,wall_limit=80):
    start=time.perf_counter()
    for _ in range(count):
        if time.perf_counter()-start>wall_limit:return 'wall_limit'
        with closing(sqlite3.connect(path)) as db:control=json.loads(db.execute('SELECT payload FROM evaluation_control').fetchone()[0])
        o=storage.observe(path,['agent-1'])[0];tick=int(o['tick']);external=[];arm=control['arm']
        if competition and control['offset']==2:
            peer=storage.observe(path,['agent-2'])[0]
            external.append((tick,dict(schema_version=1,run_id=peer['run_id'],agent_id='agent-2',request_id='evaluation-depletion',
                observation_version=peer['observation_version'],action_type='gather',target_ids=['resource-1'],parameters={'mass_kg':.4},requested_duration=1)))
        if arm.startswith('stable'):
            stable.step(path,['agent-1'],cognition.LlamaCpp(endpoint) if endpoint else None,external=external)
        else:
            if arm=='utility':
                req=choose(o,control['navigation'])
                if req:external.append((tick,req))
            storage.advance(path,1,external)
        after=storage.observe(path,['agent-1'])[0];control['offset']+=1
        with closing(sqlite3.connect(path)) as db:
            db.execute('UPDATE evaluation_control SET payload=?',(dumps(control),))
            db.execute('INSERT INTO evaluation_samples VALUES(?,?)',(int(after['tick']),dumps(dict(before=o,after=after))))
            db.commit()
    return 'target_reached'


def metrics(path,initial,scenario):
    start_tick=int(initial['tick']);final=storage.observe(path,['agent-1'])[0]
    decisions=[r for r in read(path,'decisions') if r['tick']>=start_tick and json.loads(r['request'])['agent_id']=='agent-1']
    samples=[json.loads(r['payload']) for r in read(path,'evaluation_samples')]
    receipts={r['request_id']:r for sample in samples for r in sample['after']['recent_action_results']}
    errors=Counter();completed=Counter();accepted=Counter();preventable=[];physical_failures=[]
    before_by_tick={int(s['before']['tick']):s['before'] for s in samples}
    traces=[]
    for row in decisions:
        req=json.loads(row['request']);submitted=json.loads(row['result']);receipt=receipts.get(req['request_id'])
        if submitted['status']=='accepted':accepted[req['action_type']]+=1
        if receipt and receipt['status']=='completed':completed[req['action_type']]+=1
        if receipt and receipt['status'] in ('rejected','failed'):
            error=receipt['error_code'];errors[error]+=1
            if receipt['status']=='failed':physical_failures.append(dict(request=req,receipt=receipt,classification='completion_time_physical_failure'))
            elif error in ('INSUFFICIENT_RESOURCE','OUT_OF_REACH','CAPACITY_EXCEEDED','STALE_OBSERVATION','BUSY','INVALID_ARGUMENT'):
                # Submission rejection on this unchanged single-writer tick is preventable;
                # completion-time competition is retained separately above.
                preventable.append(dict(request=req,receipt=receipt,observation=before_by_tick.get(row['tick'])))
        traces.append(dict(request=req,submitted=submitted,terminal_receipt=receipt))
    consumed={kind:int(final['own_state']['body'][kind+'_ingested_ug'])-int(initial['own_state']['body'][kind+'_ingested_ug']) for kind in ('food','water')}
    feasible={'food':scenario not in ('unavailable','depleted'),'water':True}
    achieved={'food':consumed['food']>=200000000,'water':consumed['water']>=300000000}
    needs={k:dict(mean=sum(s['after']['own_state']['body'][k] for s in samples)/max(1,len(samples)),
                   maximum=max((s['after']['own_state']['body'][k] for s in samples),default=0),
                   seconds_above_085=sum(s['after']['own_state']['body'][k]>=.85 for s in samples)) for k in ('hunger','thirst','fatigue')}
    result=dict(accepted_requests=dict(accepted),completed_actions=dict(completed),native_error_reasons=dict(errors),
        preventable_rejections=preventable,completion_time_failures=physical_failures,traces=traces,consumed_ug=consumed,
        feasible_goals=feasible,achieved_goals=achieved,missed_feasible_goals=[k for k in feasible if feasible[k] and not achieved[k]],
        alive=final['own_state']['alive'],needs=needs,simulated_s=int(final['tick'])-start_tick,final_observation=final,
        material_totals_ug=storage.inspect(path)['material_totals_ug'],replay=storage.replay(path),database_bytes=path.stat().st_size)
    if any(r['request']['action_type']=='eat' and r['submitted']['status']=='rejected' for r in traces):result['empty_eat_rejection']=True
    else:result['empty_eat_rejection']=False
    return result


def case(base,path,arm,scenario,endpoint):
    clone(base,path);initial=init_samples(path,arm);initial_totals=storage.inspect(path)['material_totals_ug']
    start=time.perf_counter();cpu=time.process_time();thought=None
    if arm.startswith('stable'):stable.attach(path,['agent-1'],model=arm=='stable_model',call_limit=1)
    if arm=='legacy_model':thought=storage.think(path,'agent-1',cognition.LlamaCpp(endpoint))
    resume=None;active=path
    if scenario=='interrupted':
        advance(path,5,endpoint)
        backup=path.with_name('resumed.sqlite');storage.save(path,'evaluation_interruption',backup)
        before=storage.inspect(path);own_memory=storage.mind(path,'agent-1');controller=stable.status(path) if arm.startswith('stable') else None
        command=[sys.executable,str(Path(__file__).resolve()),'resume','--db',str(backup),'--seconds','85']
        process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
        if process.returncode:raise RuntimeError(process.stderr)
        # Uninterrupted counterpart consumes no additional model calls (budget=1).
        advance(path,85,endpoint)
        resume=dict(returncode=process.returncode,stdout=process.stdout,
            physical_hash_matches=storage.inspect(path)['state_hash']==storage.inspect(backup)['state_hash'],
            memory_matches=storage.mind(path,'agent-1')==storage.mind(backup,'agent-1'),
            scheduler_matches=(stable.status(path)==stable.status(backup)) if controller else True,
            saved_tick=before['tick'],saved_own_memory=own_memory,saved_controller=controller)
        if not all(resume[k] for k in ('physical_hash_matches','memory_matches','scheduler_matches')):raise ValueError('resume parity failure')
        active=backup
    else:advance(path,90,endpoint,scenario=='depleted')
    result=metrics(active,initial,scenario)
    result.update(arm=arm,scenario=scenario,wall_s=time.perf_counter()-start,main_process_cpu_s=time.process_time()-cpu,
                  thought=thought,resume=resume,path=str(active),initial_observation=initial,
                  conserved=result['material_totals_ug']==initial_totals)
    if arm.startswith('stable'):
        events=[json.loads(r['payload']) for r in read(active,'stabilization_events')]
        result.update(controller=stable.status(active),controller_events=events,
                      inference_results=[e['data'] for e in events if e['kind']=='inference_result'])
    else:
        result['cognition_calls']=[json.loads(r['payload']) for r in read(active,'cognition_calls')]
        result['legacy_plans']=read(active,'plans')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['development','heldout','resume']);p.add_argument('--db',type=Path)
    p.add_argument('--seconds',type=int,default=85);args=p.parse_args()
    if args.stage=='resume':
        outcome=advance(args.db,args.seconds)
        print(json.dumps(dict(outcome=outcome,replay=storage.replay(args.db))));return
    registration=json.loads((ROOT/'artifacts/stabilization_registration.json').read_text())
    if hashlib.sha256((ROOT/'docs/STABILIZATION_PROTOCOL.md').read_bytes()).hexdigest()!=registration['protocol_sha256']:raise ValueError('protocol changed')
    folder=ROOT/f'data/stabilization-{args.stage}';folder.mkdir(exist_ok=False)
    cases=[];artifact=ROOT/f'artifacts/stabilization_{args.stage}.json'
    manifest=dict(stage=args.stage,controller_source_id=stable.source_id(),protocol_sha256=registration['protocol_sha256'],
                  native_build_id=storage.load_native().build_id,orchestration_id=storage.orchestration_id(),cases=cases)
    def run_cases(endpoint=None):
        for seed in ([101] if args.stage=='development' else [202,303,404]):
            for scenario in SCENARIOS:
                base=fixture(folder/f'{seed}-{scenario}-fixture.sqlite',seed,scenario,args.stage=='development')
                for arm in (('stable_authored',) if args.stage=='development' else ARMS):
                    result=case(base,folder/f'{seed}-{scenario}-{arm}/run.sqlite',arm,scenario,endpoint);result['seed']=seed
                    cases.append(result);write(artifact,manifest)
                    print(seed,scenario,arm,'achieved',result['achieved_goals'],'missed',result['missed_feasible_goals'],
                          'rejects',result['native_error_reasons'],'wall',round(result['wall_s'],2),flush=True)
    if args.stage=='heldout':
        # Freeze controller before first held-out measurement. Refuse a changed source.
        frozen=dict(controller_source_id=stable.source_id(),evaluation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    protocol_sha256=registration['protocol_sha256'])
        write(ROOT/'artifacts/stabilization_heldout_freeze.json',frozen)
        with model_server(folder) as endpoint:run_cases(endpoint)
    else:run_cases()
    checks=dict(stable_feasible_goals=all(not c['missed_feasible_goals'] for c in cases if c['arm'].startswith('stable')),
        stable_no_preventable_rejections=all(not c['preventable_rejections'] for c in cases if c['arm'].startswith('stable')),
        stable_no_empty_eat=all(not c['empty_eat_rejection'] for c in cases if c['arm'].startswith('stable')),
        survival=all(c['alive'] for c in cases),replay_conservation=all(c['replay']['replay_matches'] and c['conserved'] for c in cases))
    if args.stage=='heldout':
        missed={arm:sum(len(c['missed_feasible_goals']) for c in cases if c['arm']==arm) for arm in ARMS}
        checks.update(stable_no_worse_than_utility=all(missed[a]<=missed['utility'] for a in ('stable_authored','stable_model')),
            stable_model_improves_missing_legacy_goals=missed['stable_model']<missed['legacy_model'] if missed['legacy_model'] else missed['stable_model']==0,
            attributed_execution=all(e['data']['executor']=='authored_prerequisite_executor' for c in cases if c['arm'].startswith('stable') for e in c['controller_events'] if e['kind']=='request_reserved'),
            complete_durations=all(c['simulated_s']==90 for c in cases),
            resume_parity=all(c['resume'] is None or all(c['resume'][k] for k in ('physical_hash_matches','memory_matches','scheduler_matches')) for c in cases))
    manifest.update(checks=checks,passed=all(checks.values()));write(artifact,manifest)
    print(json.dumps(checks,indent=2))


if __name__=='__main__':main()
