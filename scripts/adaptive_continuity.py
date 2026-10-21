"""Continuous four-person gap profile, no replenishment or body/learner resets."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import adaptive as ad, storage, wayfinding as wf  # noqa: E402
from scripts.adaptive_study import relief,finish  # noqa: E402


def initialize(path,seed):
    ad.initialize(path,seed)
    parking=[[5,5],[5,6],[6,5],[6,6]]
    for i in range(4):
        agent=f'agent-{i+1}'
        wf.walk(path,agent,[3,3] if agent!='agent-1' else [2,3])
        relief(path,agent)
        ad.refresh(path,agent)
        wf.walk(path,agent,parking[i])
    return finish(path)


def run(path,until,wall_cap):
    start=time.perf_counter();initial=finish(path);frames=0;reason='horizon_reached'
    try:
        while storage.inspect(path)['simulated_time_s']<until:
            if time.perf_counter()-start>wall_cap:
                reason='explicit_wall_budget';break
            step=ad.cohort_step(path);frames+=1
            if step['frame']['experience']['receipt']['status']!='completed':
                reason='native_failure';break
            if frames%40==0:
                snapshot=storage.inspect(path)
                print(json.dumps(dict(frames=frames,simulated_s=snapshot['simulated_time_s'],wall_s=time.perf_counter()-start)),flush=True)
                if any(not e['alive'] for e in snapshot['entities'] if e['kind']=='actor'):
                    reason='death';break
    except ValueError as error:
        reason='explicit_stop: '+str(error)
    final=finish(path)
    with closing(storage._connect(path,readonly=True)) as db:
        operators=db.execute("SELECT COUNT(*) FROM decisions WHERE source IN ('operator','operator_knowledge')").fetchone()[0]
    return dict(path=str(path),requested_until_sim_s=until,initial=initial,final=final,
                frames=frames,stop_reason=reason,operator_interventions=operators,wall_s=time.perf_counter()-start)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','run'])
    p.add_argument('--db',type=Path,required=True);p.add_argument('--seed',type=int,default=53)
    p.add_argument('--until',type=float,default=300);p.add_argument('--wall-cap',type=float,default=600)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('do not overwrite continuity evidence')
    result=initialize(args.db,args.seed) if args.command=='init' else run(args.db,args.until,args.wall_cap)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k in ('frames','stop_reason','operator_interventions','wall_s')}))


if __name__=='__main__':main()
