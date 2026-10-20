"""Progressive finite-resource worlds; fresh-process resume and recorded-command parity."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import storage,cognition,stabilization as stable
from stabilization_common import create,model_server,read,write


def snapshot(path):
    s=storage.inspect(path)
    value=dict(tick=s['tick'],head=s['state_hash'],controller=stable.status(path),mind=storage.mind(path,'agent-1'),
               own=storage.observe(path,['agent-1'])[0]['own_state'],material_totals=s['material_totals_ug'],sources=s['boundary_sources_ug'])
    return json.loads(json.dumps(value))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['run','worker'])
    p.add_argument('--db',type=Path);p.add_argument('--seconds',type=float);p.add_argument('--wall',type=float,default=240)
    p.add_argument('--endpoint',default='http://127.0.0.1:8082');a=p.parse_args()
    if a.command=='worker':
        before=snapshot(a.db);r=stable.run(a.db,a.seconds,a.wall,cognition.LlamaCpp(a.endpoint),['agent-1'])
        print(json.dumps(dict(before=before,result=r,after=snapshot(a.db))));return
    folder=ROOT/'data/stabilization-continuity';folder.mkdir(exist_ok=False);cases=[]
    artifact=ROOT/'artifacts/stabilization_continuity.json'
    with model_server(folder) as endpoint:
        for arm in ('stable_authored','stable_model'):
            path=create(folder/f'{arm}.sqlite',seed=505,food=2,water=4,population=1)
            stable.attach(path,['agent-1'],model=arm=='stable_model',call_limit=2)
            initial=snapshot(path);started=time.perf_counter();stages=[];saved=None;active=path;cutoff=None
            for target in (30,120,600,1200):
                current=int(storage.inspect(active)['tick']);remaining=240-(time.perf_counter()-started)
                if remaining<=0:cutoff='wall_limit_before_stage';break
                before=snapshot(active)
                if target<=120:
                    result=stable.run(active,target-current,remaining,cognition.LlamaCpp(endpoint),['agent-1']);fresh=None
                else:
                    command=[sys.executable,str(Path(__file__).resolve()),'worker','--db',str(active),'--seconds',str(target-current),
                             '--wall',str(remaining),'--endpoint',endpoint]
                    process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=remaining+45)
                    if process.returncode:raise RuntimeError(process.stderr)
                    worker=json.loads(process.stdout);result=worker['result']
                    fresh=dict(returncode=process.returncode,before_matches=worker['before']==before)
                    if not fresh['before_matches']:raise ValueError('fresh process lost state before resume')
                after=snapshot(active)
                stages.append(dict(target_simulated_s=target,result=result,fresh_process=fresh,after=after,
                    conserved=after['material_totals']==initial['material_totals'],no_regeneration=after['sources']==initial['sources']))
                print(arm,target,result['status'],'tick',result['tick'],'wall',round(time.perf_counter()-started,2),flush=True)
                if result['status']!='target_reached':cutoff=result['status'];break
                if target==120:
                    backup=folder/f'{arm}-resumed.sqlite';storage.save(path,'continuous_resume',backup)
                    saved=snapshot(backup)
                    if saved!=snapshot(path):raise ValueError('saved scheduler/mind/native mismatch')
                    active=backup
            primary_wall=time.perf_counter()-started
            final=snapshot(active);parity=None
            if saved and int(final['tick'])>120:
                # Same committed requests; no regenerated choices or replenished state.
                decisions=[(r['tick'],json.loads(r['request'])) for r in read(active,'decisions') if r['tick']>=120]
                parity_started=time.perf_counter();storage.advance(path,int(final['tick'])-120,decisions)
                parity=dict(native_hash_matches=storage.inspect(path)['state_hash']==final['head'],
                    own_memory_matches=storage.mind(path,'agent-1')==storage.mind(active,'agent-1'),
                    wall_s=time.perf_counter()-parity_started,method='uninterrupted native continuation with recorded requests; no inference rerun',
                    replay=storage.replay(path))
                if not parity['native_hash_matches'] or not parity['own_memory_matches']:raise ValueError('continuous recorded-command parity failed')
            case=dict(arm=arm,initial=initial,stages=stages,final=final,primary_wall_s=primary_wall,cutoff=cutoff,
                recorded_command_parity=parity,controller_source_id=stable.source_id(),final_replay=storage.replay(active),path=str(active))
            cases.append(case);write(artifact,dict(cases=cases,scope='finite continuous worlds; 240 primary wall seconds per arm; separate recorded-command parity cost'))
    checks=dict(survival=all(c['final']['own']['alive'] for c in cases),
        conservation=all(s['conserved'] and s['no_regeneration'] for c in cases for s in c['stages']),
        fresh_process_continuity=all(s['fresh_process'] is None or s['fresh_process']['before_matches'] for c in cases for s in c['stages']),
        replay=all(c['final_replay']['replay_matches'] for c in cases),
        maximum_horizon_completed=all(int(c['final']['tick'])==1200 for c in cases))
    write(artifact,dict(cases=cases,checks=checks,scope='finite continuous worlds; 240 primary wall seconds per arm; separate recorded-command parity cost'))


if __name__=='__main__':main()
