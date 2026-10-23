"""Secondary matched continuation control from an existing actual life; no resets."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import adaptive as ad,developmental as dev,storage,wayfinding as wf  # noqa: E402
from scripts.adaptive_study import finish  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--until',type=float,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('do not overwrite continuity control evidence')
    args.directory.mkdir(parents=True,exist_ok=False);common=args.directory/'common.sqlite'
    storage.save(args.source,'gap-control-'+dev.digest(str(args.directory.resolve()))[:12],common)
    # Give both policies the same genuinely observed legacy source memories too.
    for i in range(4):
        for kind in ('food','water'):wf.observe_source(common,f'agent-{i+1}',kind)
    initial=finish(common);runs={}
    for mode in ('adaptive','legacy'):
        path=args.directory/(mode+'.sqlite');storage.save(common,mode,path)
        start=time.perf_counter();frames=goals=0;reason='horizon_reached'
        try:
            while storage.inspect(path)['simulated_time_s']<args.until:
                if time.perf_counter()-start>600:reason='wall_budget';break
                if mode=='adaptive':
                    r=ad.cohort_step(path);goals+=r['frame']['goal_completed']
                else:
                    r=wf.policy_step(path,f'agent-{frames%4+1}');goals+=bool(r['execution'] and r['execution']['goal_completed'])
                frames+=1
        except ValueError as error:reason='explicit_stop: '+str(error)
        final=finish(path)
        with closing(storage._connect(path,readonly=True)) as db:
            operators=db.execute("SELECT COUNT(*) FROM decisions WHERE source IN ('operator','operator_knowledge')").fetchone()[0]
        runs[mode]=dict(path=str(path),frames=frames,new_completed_goals=goals,stop_reason=reason,
            wall_s=time.perf_counter()-start,operator_interventions=operators,final=final)
        print(json.dumps(dict(mode=mode,goals=goals,stop=reason,simulated_s=final['snapshot']['simulated_time_s'])),flush=True)
    result=dict(source=str(args.source),initial=initial,runs=runs,
        scope='secondary development control from a matched continued life; not five independent survival seeds')
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
