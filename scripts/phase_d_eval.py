"""Bounded native ecology study. Fixtures and care routes are authored, not learned.

Thresholds precede measurement in docs/PHASE_D_ECOLOGY.md. This tool creates a
NEW output directory and preserves raw receipts, checkpoints and timings.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from ecology_fixtures import caretaker_layout, harness, balances
from underworld.native import load_native


def digest(w):return hashlib.sha256(w.checkpoint().encode()).hexdigest()


def until(w,seconds):
    ticks=round(seconds/w.snapshot()['dt_s'])-int(w.snapshot()['tick'])
    if ticks>0:w.step(ticks)


def care(h,at,failures):
    """Bounded operator-assigned care; only own observations select targets."""
    def act(kind,targets=(),params=None,duration=1):
        try:return h.act(kind,targets,params,duration)
        except AssertionError as e:failures.append({'at_s':at,'action':kind,'receipt':str(e)});return None
    def approach(id):
        for attempt in range(3):
            o=h.observe();target=next((e for e in o['visible_entities'] if e['entity_id']==id),None)
            if not target:return False
            p=o['own_state']['position_m'];q=target['position_m'];d=math.dist(p,q)
            if d<=1.25:return True
            # One authored local approach, with bounded retries; no hidden map.
            goal=[q[i]+(p[i]-q[i])/d*1.0 for i in (0,1)]
            if not act('move',params={'x_m':goal[0],'y_m':goal[1]},duration=max(1,d+1)):
                # An observed obstruction remains a recorded failure; no teleport.
                return False
        return False
    if at in (0,160) and approach('care-trough'):
        act('fill_trough',['care-trough'],{'material':'water','mass_kg':.5})
    for id in ('animal-1','animal-2'):
        if not approach(id):continue
        act('observe_animal',[id],duration=.2)
        act('offer_feed',[id],{'material':'food','mass_kg':.1})
        if at>0:
            report=act('observe_animal',[id],duration=.2)
            if report:
                amount=int(report['observable_effects']['description'].split(':eggs_ug=')[-1])
                if amount>=60000000 and act('collect_eggs',[id],{'material':'eggs','mass_kg':.06}):
                    act('eat',params={'material':'eggs','mass_kg':.06},duration=2)


def summary(w):
    s=w.snapshot()
    return {'simulated_s':s['simulated_time_s'],'tick':s['tick'],'native_head':digest(w),'balances':balances(w),
            'animals':{e['entity_id']:{'alive':e['alive'],'condition':e['condition'],'position_m':e['position_m'],'body':e['body']} for e in s['entities'] if e['kind']=='animal'},
            'ecology':s['ecology'],'boundary_sources_ug':s['boundary_sources_ug'],'event_counts':s['event_counts']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    result={'kind':'living-world-d-ecology-evaluation','native_build_id':load_native().build_id,'protocol_sha256':hashlib.sha256((ROOT/'docs/PHASE_D_ECOLOGY.md').read_bytes()).hexdigest(),
            'origin':'authored_native_behavior_and_operator_assigned_care','model_calls':0,'development_seeds':[21],'heldout_seeds':[303,404],'runs':[]}
    for seed in (21,303,404):
        for treatment in ('deprived','caretaking'):
            start=time.perf_counter();w=caretaker_layout(seed);h=harness(w);failures=[];stages=[];checkpoint=None;future_index=0
            name=f'{seed}-{treatment}';(args.output/f'{name}-initial.txt').write_text(w.checkpoint())
            for at in (0,30,80,120,160,240,300):
                until(w,at)
                if at in (0,80,160,240) and treatment=='caretaking':care(h,at,failures)
                if at in (30,120,300):
                    stages.append(summary(w))
                    if at==120:checkpoint=w.checkpoint();future_index=len(h.receipts)
            primary_wall=time.perf_counter()-start
            (args.output/f'{name}-final.txt').write_text(w.checkpoint());(args.output/f'{name}-mid.txt').write_text(checkpoint)
            shadow_start=time.perf_counter();shadow=load_native().World.restore(checkpoint)
            for row in h.receipts[future_index:]:
                request=row['request'];target=int(request['observation_version']);current=int(shadow.snapshot()['tick'])
                if target>current:shadow.step(target-current)
                shadow.submit(request,request['agent_id'])
            shadow.step(int(w.snapshot()['tick'])-int(shadow.snapshot()['tick']))
            resumed_equal=shadow.checkpoint()==w.checkpoint();shadow_wall=time.perf_counter()-shadow_start
            row={'seed':seed,'treatment':treatment,'simulated_s':w.snapshot()['simulated_time_s'],'wall_s':primary_wall,'resume_wall_s':shadow_wall,'resume_exact':resumed_equal,
                 'stages':stages,'requests':h.receipts,'authored_route_failures':failures,'accepted':sum(r['submitted']['status']=='accepted' for r in h.receipts),
                 'completed':sum(r.get('terminal',{}).get('status')=='completed' for r in h.receipts)}
            result['runs'].append(row)
    gates={}
    for seed in (21,303,404):
        poor,good=[next(r for r in result['runs'] if r['seed']==seed and r['treatment']==t) for t in ('deprived','caretaking')]
        gates[str(seed)]={'care_improves_condition':sum(v['alive'] for v in good['stages'][-1]['animals'].values())>sum(v['alive'] for v in poor['stages'][-1]['animals'].values()),
                          'reserve_funded_eggs':int(good['stages'][-1]['ecology']['eggs_produced_ug'])>0,
                          'exact_resume':good['resume_exact'] and poor['resume_exact'],
                          'zero_balance_error':all(not any(stage['balances'].values()) for r in (poor,good) for stage in r['stages'])}
    result['gates']=gates;result['passed']=all(all(g.values()) for g in gates.values())
    args.evidence.parent.mkdir(parents=True,exist_ok=True);args.evidence.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'gates':gates,'runs':[{k:r[k] for k in ('seed','treatment','simulated_s','wall_s','resume_exact','accepted','completed','authored_route_failures')} for r in result['runs']]},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':sys.exit(main())
