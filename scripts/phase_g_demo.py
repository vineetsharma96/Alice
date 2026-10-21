"""Finite four-person integration, separate unassigned/assigned authored arms."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage,stabilization as stable,planning,knowledge,care,teaching,runtime,memory  # noqa: E402
from underworld.config import load  # noqa: E402


def collect(path):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');world,_,_,_=storage._head(db);world.check_invariants();snapshot=world.snapshot()
        states={a:stable._load(db,a) for a, in db.execute('SELECT agent FROM stabilization_agents')}
        decisions=[{'tick':t,'request':json.loads(q),'result':json.loads(r),'source':s}
                   for t,q,r,s in db.execute('SELECT tick,request,result,source FROM decisions ORDER BY id')]
        events=[json.loads(r[0]) for r in db.execute('SELECT payload FROM events ORDER BY seq')]
        know={a:knowledge.projection(db,a) for a in states}
        m={k:int(v) for k,v in snapshot['material_totals_ug'].items()};eco=snapshot['ecology']
        food=sum(m.get(k,0) for k in ('food','forage','plant_food','eggs'))+int(eco['food_residue_ug'])+sum(int(a['food_reserve_ug']) for a in eco['animals'].values())
        water=m.get('water',0)+int(eco['water_waste_ug'])+sum(int(a['water_reserve_ug']) for a in eco['animals'].values())
        balances={'food_error_ug':food-snapshot['initial_mass_ug']['food']-snapshot['boundary_sources_ug']['food'],
                  'water_error_ug':water-snapshot['initial_mass_ug']['water']-snapshot['boundary_sources_ug']['water'],
                  'animal_body_error_ug':m.get('animal',0)-int(eco['structural_body_initial_ug'])}
        assert not any(balances.values()),balances
        return dict(snapshot=snapshot,states=states,knowledge=know,decisions=decisions,events=events,
                    balances=balances,cognitive_hash=memory.checksum(db),database_bytes=Path(path).stat().st_size,
                    archive_bytes=sum(p.stat().st_size for p in Path(str(path)+'.epochs').glob('*.sqlite')),
                    archive_state=runtime.verify_control(db))


def initialize(path,seed):
    config=load(ROOT/'config/living-world-g.toml');config['seed']=seed
    stable.initialize(path,config,call_limit=0,knowledge_profile={'profile':'woodcraft','recipient':'agent-1'})
    before=storage.inspect(path)
    teaching.intervene(path,{'schema_version':1,'run_id':before['run_id'],'branch_id':before['branch_id'],
        'intervention_id':'g-care','observation_version':before['tick'],'kind':'inject_knowledge',
        'parameters':{'recipient':'agent-2','text':care.text()}})
    assert storage.inspect(path)['state_hash']==before['state_hash']
    lesson=knowledge.view(path,'agent-2')['records'][0]['episode_id']
    assert all(knowledge.view(path,a)['counts']['operator_injection']==0 for a in ('agent-1','agent-3','agent-4'))
    with closing(storage._connect(path,readonly=True)) as db:
        world,_,_,_=storage._head(db);native_hash=hashlib.sha256(world.checkpoint().encode()).hexdigest()
    return config,lesson,native_hash


def run_case(directory,seed,arm,horizons,wall_limit):
    path=directory/f'{seed}-{arm}.sqlite';config,lesson,initial_hash=initialize(path,seed)
    queues={'agent-1':[('craft_tool',{}),('build_pen',{'position_m':[11,11]})],
            'agent-2':[('feed_animal',{'target':'animal-1','lesson_episode_id':lesson}),
                       ('provide_water',{'position_m':[5.5,4.8]}),('tend_animal',{'target':'animal-1'})],
            'agent-3':[('obtain_food',{'mass_kg':.1}),('rest',{})]} if arm=='assigned' else {}
    started=time.perf_counter();result={'seed':seed,'arm':arm,'path':str(path),'initial_native_hash':initial_hash,
        'config':config,'stages':[],'assignments':[],'execution':'authored','model_calls':0}
    decisions={};events={}
    def retain(state):
        for d in state['decisions']:
            r=d['request'];key=(r.get('agent_id'),r.get('request_id',r.get('intervention_id')))
            decisions[key]=d
        for event in state['events']:events[event['seq']]=event
    for horizon in horizons:
        stage_start=time.perf_counter();outcome='target_reached';last=None
        while storage.inspect(path)['simulated_time_s']<horizon-1e-9:
            remaining=wall_limit-(time.perf_counter()-stage_start)
            if remaining<=0:outcome='wall_limit';break
            current=collect(path);retain(current)
            for agent,queue in queues.items():
                if queue and not current['states'][agent].get('tasks',{}).get('active'):
                    own=storage.observe(path,[agent])[0]['own_state']
                    if not own['alive']:continue
                    goal,params=queue.pop(0)
                    planning.assign(path,agent,goal,params)
                    result['assignments'].append({'tick':current['snapshot']['tick'],'agent':agent,'goal':goal,'params':params,'origin':'explicit_operator_assigned_authored_procedure'})
            remaining=wall_limit-(time.perf_counter()-stage_start)
            if remaining<=0:outcome='wall_limit';break
            seconds=min(20,horizon-current['snapshot']['simulated_time_s'])
            last=stable.run(path,seconds,max(.1,remaining))
            if last['status']!='target_reached':outcome=last['status'];break
        current=collect(path);retain(current)
        result['stages'].append({'target_simulated_s':horizon,'status':outcome,'wall_s':time.perf_counter()-stage_start,
                                 'actual_simulated_s':current['snapshot']['simulated_time_s'],'state':current})
        result.update(wall_s=time.perf_counter()-started,remaining_assignments=queues,
                      decisions=list(decisions.values()),events=sorted(events.values(),key=lambda e:int(e['seq'])))
        result['replay']=storage.replay(path);result['archives']=runtime.verify_archives(path)
        result['model_calls']=sum(s['calls']+s.get('tasks',{}).get('calls',0) for s in current['states'].values())
        (directory/f'{seed}-{arm}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'seed':seed,'arm':arm,'target':horizon,'actual':current['snapshot']['simulated_time_s'],
                          'status':outcome,'wall_s':result['stages'][-1]['wall_s'],
                          'goals':{a:s.get('tasks',{}).get('history',[]) for a,s in current['states'].items()}}),flush=True)
        if outcome!='target_reached':break
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',choices=['development','confirmation'],required=True)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--horizons',default='60,300,900');p.add_argument('--wall-seconds',type=float,default=240)
    p.add_argument('--arms',nargs='+',choices=['unassigned','assigned'],default=['unassigned','assigned'])
    args=p.parse_args();horizons=list(map(float,args.horizons.split(',')))
    if not horizons or sorted(set(horizons))!=horizons or horizons[0]<=0 or horizons[-1]>900 or not 0<args.wall_seconds<=240:
        p.error('increasing horizons <=900 and wall budget <=240 required')
    args.directory=args.directory.resolve()
    args.directory.mkdir(parents=True,exist_ok=False);seeds=[21] if args.split=='development' else [2521,2549]
    report={'split':args.split,'protocol':'docs/PHASE_G_INTEGRATION.md','runs':[],'controller_source_id':stable.source_id()}
    for seed in seeds:
        for arm in args.arms:
            report['runs'].append(run_case(args.directory,seed,arm,horizons,args.wall_seconds))
            report['matched_initial_physics']=all(len({r['initial_native_hash'] for r in report['runs'] if r['seed']==s})==1 for s in seeds if any(r['seed']==s for r in report['runs']))
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert report['matched_initial_physics']


if __name__=='__main__':main()
