"""Compare the frozen pre-repair executor with the authored edible-food repair."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_food_execution import fixture, state
from ecology_fixtures import balances, harness, layout, world
from underworld import stabilization
from underworld.native import load_native


def initial(seed,case):
    w=fixture(seed,forage=.2 if case in ('forage','carried_plant','expiring') else 0)
    h=harness(w)
    if case in ('carried_plant','expiring'):
        h.act('gather_plant',['forage-1'],{'mass_kg':.2})
        if case=='expiring':h.step(590)
    if case=='eggs':
        w=layout(world(seed,forage=0),positions={'agent-1':(3,4.5),'animal-1':(5,5),'animal-2':(4,4.5),'resource-1':(20,3)},fatigue=.95)
        w.step(150);h=harness(w)
        h.act('collect_eggs',['animal-2'],{'material':'eggs','mass_kg':.06})
    return w.checkpoint()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=ROOT/'build/runtime-before-food-fix-20261021/underworld/stabilization.py')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('underworld._food_baseline',args.baseline)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    result=dict(protocol_sha256=hashlib.sha256((ROOT/'docs/FOOD_EXECUTION_PROTOCOL.md').read_bytes()).hexdigest(),
                baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
                candidate_sha256=stabilization.source_id(),model_calls=0,origin='authored_execution',
                development_seeds=[21],confirmation_seeds=[717,818],runs=[])
    for seed in (21,717,818):
        for case in ('carried_plant','eggs','forage','empty','expiring'):
            checkpoint=initial(seed,case)
            (args.output/f'{seed}-{case}-initial.txt').write_text(checkpoint)
            for arm,planner in (('baseline',old),('candidate',stabilization)):
                started=time.perf_counter();w=load_native().World.restore(checkpoint);h=harness(w)
                o=h.observe();s=state(o);start_tick=int(o['tick']);before=int(o['own_state']['body']['food_ingested_ug']);blocked=None
                for _ in range(8):
                    o=h.observe()
                    if int(o['own_state']['body']['food_ingested_ug'])-before>=200000000:break
                    req,blocked=planner._next(s,o)
                    if not req:break
                    try:h.act(req['action_type'],req['target_ids'],req['parameters'],req['requested_duration'])
                    except AssertionError:break
                after=h.observe();delta=int(after['own_state']['body']['food_ingested_ug'])-before
                rows=h.receipts
                result['runs'].append(dict(seed=seed,case=case,arm=arm,wall_s=time.perf_counter()-started,
                    simulated_s=(int(after['tick'])-start_tick)*after['dt_s'],ingested_ug=delta,
                    goal_completed=delta>=200000000,completed=sum(r.get('terminal',{}).get('status')=='completed' for r in rows),
                    rejected=sum(r['submitted']['status']=='rejected' for r in rows),
                    failed=sum(r.get('terminal',{}).get('status')=='failed' for r in rows),
                    alive=after['own_state']['alive'],blocked=blocked,balances=balances(w),requests=rows))
                (args.output/f'{seed}-{case}-{arm}-final.txt').write_text(w.checkpoint())
    candidate=[r for r in result['runs'] if r['arm']=='candidate']
    result['passed']=all(not any(r['balances'].values()) for r in result['runs']) and all(
        r['rejected']==r['failed']==0 and
        (r['goal_completed'] if r['case'] in ('carried_plant','forage') else
         r['ingested_ug']==60000000 if r['case']=='eggs' else r['ingested_ug']==0)
        for r in candidate)
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'runs':[{k:v for k,v in r.items() if k!='requests'} for r in result['runs']]},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
