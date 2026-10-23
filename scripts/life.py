"""Create an explicit integrated copy, continue every inhabitant, inspect/replay."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import life_store as store, weather_store as weather


def report(path):
    state=store.inspect(path);actions=Counter();origins=Counter();rejections=Counter();turns=Counter()
    accepted=0;completed=0;goals=0;inferred_accepted=0;direct_ids=set()
    with closing(weather.connect(path)) as db:
        for raw,expected in db.execute('SELECT command,result FROM weather_operations'):
            command=json.loads(raw);result=json.loads(expected)
            if command['kind']=='submit' and result['status']=='accepted':
                accepted+=1;direct_ids.add(command['request']['request_id'])
        for raw,result in db.execute('SELECT command,result FROM life_operations'):
            command=json.loads(raw);r=json.loads(result);n=r['native']
            if command['kind']=='emotion-policy':turns[command['agent']]+=1
            if not isinstance(n,dict) or 'request' not in n:continue
            action=n['request']['action_type'];actions[action]+=1
            receipt=n['receipt'];completed+=receipt['status']=='completed'
            if n['request']['request_id'] not in direct_ids and receipt['status'] in ('completed','failed','expired'):
                inferred_accepted+=1
            if receipt['status']!='completed':rejections[receipt['error_code']]+=1
            influence=r['influence']
            origins[influence['origin'] if influence and influence['changed'] else n['choice']['origin']]+=1
            if receipt['status']=='completed' and action in ('eat','drink'):
                key='hunger' if action=='eat' else 'thirst'
                goals+=n['before']['own_state']['body'][key]>n['after']['own_state']['body'][key]
        bytes_by_person={a:len(weather.dumps(s).encode()) for a,s in state['people'].items()}
    actors=[e for e in state['snapshot']['entities'] if e['kind']=='actor']
    return dict(simulated_s=state['snapshot']['simulated_time_s'],tick=state['snapshot']['tick'],
        alive=sum(e['alive'] for e in actors),population=len(actors),
        actions=dict(actions),accepted_requests=accepted+inferred_accepted,
        directly_recorded_acceptances=accepted,acceptances_implied_by_terminal_receipt=inferred_accepted,
        completed_actions=completed,
        achieved_need_goals=goals,rejections=dict(rejections),decision_origins=dict(origins),
        scheduled_turns=dict(turns),next_turn=store.next_turn(path),
        unmet_needs={e['entity_id']:e['body'] for e in actors},
        material_totals_ug=state['snapshot']['material_totals_ug'],
        boundary_sources_ug=state['snapshot']['boundary_sources_ug'],
        operator_sources_ug=state['snapshot']['operator_sources_ug'],
        source_hash=state['hash'],operations=state['operations'],private_state_bytes=bytes_by_person,
        social={a:dict(deliveries=s['life']['deliveries'],grounded=s['life']['grounded'],
            help_received=s['life']['help_received'],relationships=len(s['life']['relationships']),
            inferences=len(s['life']['inferences']),social_states=sorted(s['life']['social']['states']),
            preferences=s['life']['values']['acquired_preferences']) for a,s in state['people'].items()})


def run(path,until,wall_budget=600):
    if type(until) not in (int,float) or not math.isfinite(until) or until<0:raise ValueError('Finite absolute horizon required')
    if not math.isfinite(wall_budget) or wall_budget<=0:raise ValueError('Positive finite wall budget required')
    started=time.perf_counter();initial=store.inspect(path);dt=initial['snapshot']['dt_s']
    if abs(until-round(until/dt)*dt)>1e-9:raise ValueError('Horizon must be a native tick boundary')
    status='target_reached'
    while True:
        current=store.inspect(path);remaining=until-current['snapshot']['simulated_time_s']
        if remaining<=0:break
        if time.perf_counter()-started>=wall_budget:status='wall_limit';break
        if any(not e['alive'] for e in current['snapshot']['entities'] if e['kind']=='actor'):status='death';break
        agent,cursor=store.next_turn(path)
        # A final tick-aligned step reaches the exact horizon, preserving pending
        # actions. A policy action can extend by at most its declared duration.
        command=dict(kind='step',ticks=round(remaining/dt)) if remaining<5 else dict(kind='emotion-policy',agent=agent)
        store.commit(path,command,f"life-turn-{current['operations']}")
    result=report(path);result.update(status=status,initial_simulated_s=initial['snapshot']['simulated_time_s'],
        simulated_duration_s=result['simulated_s']-initial['snapshot']['simulated_time_s'],
        execution_wall_s=time.perf_counter()-started)
    replay_start=time.perf_counter();result['replay']=store.replay(path)
    result['replay_wall_s']=time.perf_counter()-replay_start;result['total_wall_s']=time.perf_counter()-started
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    new=sub.add_parser('new');new.add_argument('--source',type=Path,required=True);new.add_argument('--db',type=Path,required=True)
    new.add_argument('--seed',type=int,default=61);new.add_argument('--population',type=int,default=4)
    attach=sub.add_parser('attach');attach.add_argument('--source',type=Path,required=True);attach.add_argument('--db',type=Path,required=True)
    for p in (new,attach):p.add_argument('--mode',choices=store.life_affect.MODES,default='connected')
    for name in ('inspect','replay','run','save'):
        p=sub.add_parser(name);p.add_argument('--db',type=Path,required=True)
        if name=='run':
            p.add_argument('--until',type=float,required=True);p.add_argument('--wall-budget',type=float,default=600)
            p.add_argument('--output',type=Path,required=True)
        if name=='save':p.add_argument('--destination',type=Path,required=True)
    a=parser.parse_args()
    if a.command=='new':store.initialize_source(a.source,seed=a.seed,population=a.population)
    if a.command in ('new','attach'):
        before=hashlib.sha256(a.source.read_bytes()).hexdigest();store.attach(a.source,a.db,mode=a.mode)
        assert before==hashlib.sha256(a.source.read_bytes()).hexdigest();result=report(a.db)
    elif a.command=='run':
        if a.output.exists():parser.error('Refuse overwriting experiment evidence')
        result=run(a.db,a.until,a.wall_budget);a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    elif a.command=='replay':result=store.replay(a.db)
    elif a.command=='save':weather.save(a.db,a.destination);result=store.inspect(a.destination)
    else:result=report(a.db)
    print(json.dumps(result,allow_nan=False))


if __name__=='__main__':main()
