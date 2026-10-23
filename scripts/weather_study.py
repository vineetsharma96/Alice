"""Prospective W6 native weather comparison; distinct development and held-out saves."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import weather_store as store  # noqa: E402
from underworld.weather_runtime import climate,load  # noqa: E402
from underworld.weather_tools import JournalWorld,execute,ingredients,move,request,roof,site,walk  # noqa: E402

HELDOUT=[13001,13007,13009]
CONDITIONS={53:(-10,12,4),71:(-6,8,2),13001:(-6,8,2),13007:(-10,10,4),13009:(-14,12,6)}


def sources():
    files=[]
    for folder in ['weather_native','weather_tests']:
        files.extend(p for p in (ROOT/folder).glob('*') if p.is_file())
    files.extend((ROOT/'underworld').glob('weather*.py'))
    files.extend((ROOT/'underworld/web').glob('weather.*'))
    files.extend(ROOT/p for p in ['scripts/weather.py','scripts/weather_demo.py','scripts/weather_study.py',
                                  'scripts/verify_weather_viewer.mjs','scripts/build_weather.ps1','scripts/weather_audit.py',
                                  'docs/WEATHER_CONTRACT.md','docs/WEATHER_EVALUATION_PROTOCOL.md',
                                  'config/weather-research.toml','config/weather-normal.toml'])
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}


def initialize(path,seed,population=1):
    store.initialize(path,seed,population,climate(),True,food_kg=8,water_kg=16)
    return JournalWorld(path)


def force(path,seed,mild=False):
    temp,rain,wind=(20,0,0) if mild else CONDITIONS[seed]
    version=store.inspect(path)['snapshot']['tick']
    payload=dict(id='controlled-weather',observation_version=version,duration_s=600,temperature_c=temp,
                 rain_mm_h=rain,cloud_fraction=.0 if mild else .9,wind_x_m_s=wind,wind_y_m_s=0 if mild else 1)
    store.commit(path,dict(kind='force',parameters=payload))
    return payload


def finish(path):
    w=JournalWorld(path);w.check_invariants()
    counts=dict(accepted_submissions=0,completed_policy_actions=0,policy_rejections=0)
    errors=[]
    with closing(store.connect(path)) as db:
        for command,result_json in db.execute('SELECT command,result FROM weather_operations ORDER BY seq'):
            command,result=json.loads(command),json.loads(result_json)
            if command['kind']=='submit' and result['status']=='accepted':counts['accepted_submissions']+=1
            if command['kind'] in ('policy','cohort') and 'receipt' in result:
                if result['receipt']['status']=='completed':counts['completed_policy_actions']+=1
                else:counts['policy_rejections']+=1;errors.append(result['receipt'])
    final=store.inspect(path)
    return dict(**final,replay=store.replay(path),counts=counts,native_failures=errors,
                sqlite_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


def run_policy(path,until,mode='weather',cohort=False,wall_cap=600):
    start=time.perf_counter();steps=0;protected={};max_occupancy=0;tail=0;reason='horizon_reached'
    initial=store.inspect(path);initial_time=initial['snapshot']['simulated_time_s']
    while True:
        current=store.inspect(path);clock=current['snapshot']['simulated_time_s']
        if clock>=until:break
        if time.perf_counter()-start>wall_cap:reason='wall_budget';break
        if any(not e['alive'] for e in current['snapshot']['entities'] if e['kind']=='actor'):reason='death';break
        remaining=until-clock
        if remaining<5:
            tail=remaining;store.commit(path,dict(kind='step',ticks=round(remaining/current['snapshot']['dt_s'])));continue
        command=dict(kind='cohort' if cohort else 'policy',mode=mode)
        if not cohort:command['agent']='agent-1'
        store.commit(path,command);steps+=1
        after=store.inspect(path)
        covered=[a for a,e in after['climate']['exposure'].items() if e['shelter_id']]
        max_occupancy=max(max_occupancy,len(covered))
        for a in covered:protected.setdefault(a,after['snapshot']['simulated_time_s']-initial_time)
    return dict(initial=initial,final=finish(path),steps=steps,first_protection_s=protected,
                max_protected=max_occupancy,idle_tail_s=tail,stop_reason=reason,wall_s=time.perf_counter()-start)


def restarts(seed):
    w=load().World(seed=seed,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True)
    w.configure_climate(climate());w.step(395)
    results={}
    with tempfile.TemporaryDirectory(prefix='weather-native-resume-') as directory:
        for label,ticks in [('mid_transition',37),('mid_build',28),('in_shelter',37)]:
            if label=='mid_build':
                ingredients(w);target=site(w)
                w.submit(request(w,'work_construction',target,duration=12),'agent-1');w.step(20)
            if label=='in_shelter':move(w,[4,4]);w.step(9)
            p=Path(directory)/'state.txt';p.write_text(w.checkpoint(),encoding='utf8')
            code="from pathlib import Path;import sys;from underworld.weather_runtime import load;w=load().World.restore(Path(sys.argv[1]).read_text(encoding='utf8'),'test');w.step(int(sys.argv[2]));print(w.checkpoint())"
            resumed=subprocess.check_output([sys.executable,'-c',code,str(p),str(ticks)],cwd=ROOT,text=True).removesuffix('\n')
            w.step(ticks);results[label]=w.checkpoint()==resumed
    return results


def cases(directory,seed):
    directory.mkdir(parents=True,exist_ok=False);start=time.perf_counter();result={}
    mild=directory/'mild.sqlite';w=initialize(mild,seed);force(mild,seed,True);w.step(400)
    result['mild']=finish(mild)
    base=directory/'reachable-common.sqlite';w=initialize(base,seed);roof(w);force(base,seed)
    arms={}
    for mode in ('survival','weather'):
        p=directory/f'reachable-{mode}.sqlite';store.save(base,p)
        arms[mode]=run_policy(p,w.snapshot()['simulated_time_s']+120,mode)
    result['reachable']=arms
    build=directory/'build.sqlite';w=initialize(build,seed);ingredients(w);force(build,seed)
    result['build']=run_policy(build,w.snapshot()['simulated_time_s']+120)
    blocked=directory/'blocked.sqlite';w=initialize(blocked,seed);ingredients(w)
    before=w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug']
    refused=execute(w,'begin_construction',parameters=dict(recipe_id='lean_to',x_m=2.8,y_m=4))
    same=before==w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug']
    # Actual first construction exhausts carried fiber; second request cannot
    # invent another roof. This is batch scarcity, not global wood extinction.
    target=site(w);execute(w,'work_construction',target,duration=12)
    scarce=execute(w,'begin_construction',parameters=dict(recipe_id='lean_to',x_m=1.2,y_m=4))
    result['scarcity']=dict(blocked_receipt=refused,blocked_inventory_unchanged=same,
                            depleted_carried_batch_receipt=scarce,scope='carried fiber exhausted; not all regional wood depleted',final=finish(blocked))
    share=directory/'sharing.sqlite';w=initialize(share,seed,4)
    for i in range(2,5):walk(w,[8,3+i],f'agent-{i}')
    roof(w)
    positions=([2.6,4],[4,2.6],[5.4,4],[4,5.4])
    for i,q in enumerate(positions,1):walk(w,q,f'agent-{i}')
    force(share,seed);result['sharing']=run_policy(share,w.snapshot()['simulated_time_s']+120,cohort=True)
    grown=load().World(seed=seed,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True,tree_growth_kg_s=.001)
    grown.configure_climate(climate());grown.configure_ecology(forage_kg=0,regeneration_kg_s=.001);grown.step(400);grown.check_invariants()
    static=load().World(seed=seed,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True)
    static.configure_climate(climate());static.configure_ecology(forage_kg=0,regeneration_kg_s=0);static.step(400);static.check_invariants()
    result['growth']=dict(grown=grown.snapshot(),zero=static.snapshot())
    result['restart']=restarts(seed)
    a=arms['weather']['final']['climate']['exposure']['agent-1'];b=arms['survival']['final']['climate']['exposure']['agent-1']
    result['gates']=dict(mild=result['mild']['climate']['exposure']['agent-1']['environmental_health_lost']<=1e-12,
        reachable=arms['weather']['initial']['state_hash']==arms['survival']['initial']['state_hash'] and arms['weather']['first_protection_s'].get('agent-1',1e9)<=60 and b['environmental_health_lost']-a['environmental_health_lost']>=.02 and
            next(e['body']['health'] for e in arms['weather']['final']['snapshot']['entities'] if e['entity_id']=='agent-1')>=next(e['body']['health'] for e in arms['survival']['final']['snapshot']['entities'] if e['entity_id']=='agent-1'),
        build=bool(result['build']['final']['climate']['shelters']) and bool(result['build']['first_protection_s']),
        scarcity=refused['error_code']=='NO_PLACEMENT' and same and scarce['error_code']=='INSUFFICIENT_RESOURCE',
        sharing=len(result['sharing']['first_protection_s'])==4 and result['sharing']['max_protected']==4,
        growth=0<grown.snapshot()['boundary_sources_ug']['tree']<100000000 and 0<grown.snapshot()['boundary_sources_ug']['food']<100000000 and static.snapshot()['boundary_sources_ug']['tree']==0 and static.snapshot()['boundary_sources_ug']['food']==0,
        restart=all(result['restart'].values()))
    result['seed']=seed;result['weather_forcing']=CONDITIONS[seed];result['wall_s']=time.perf_counter()-start
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['register','run','continuity'])
    p.add_argument('--directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--development',action='store_true');p.add_argument('--registration',type=Path,default=ROOT/'artifacts/weather_registration.json')
    p.add_argument('--db',type=Path);p.add_argument('--until',type=float,default=300);args=p.parse_args()
    if args.output.exists():raise ValueError('Do not overwrite weather evidence')
    if args.command=='register':result=dict(seeds=HELDOUT,files=sources(),native_build_id=load().build_id)
    elif args.command=='continuity':
        if not args.db:raise ValueError('continuity needs --db')
        if not args.db.exists():
            w=initialize(args.db,53,4)
            for i in range(2,5):walk(w,[8,3+i],f'agent-{i}')
            roof(w)
            for i,q in enumerate(([3.7,3.7],[4.3,3.7],[3.7,4.3],[4.3,4.3]),1):walk(w,q,f'agent-{i}')
        result=run_policy(args.db,args.until,cohort=True)
    else:
        if not args.directory:raise ValueError('run needs --directory')
        if not args.development and json.loads(args.registration.read_bytes())['files']!=sources():raise ValueError('Weather source registration mismatch')
        args.directory.mkdir(parents=True,exist_ok=False);start=time.perf_counter();runs=[]
        for seed in ([53,71] if args.development else HELDOUT):
            runs.append(cases(args.directory/str(seed),seed))
            print(json.dumps(dict(seed=seed,gates=runs[-1]['gates'],wall_s=runs[-1]['wall_s'])),flush=True)
            if runs[-1]['wall_s']>600 or time.perf_counter()-start>1200:raise TimeoutError('Weather evaluation compute cap')
        result=dict(development=args.development,files=sources(),runs=runs,wall_s=time.perf_counter()-start)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
