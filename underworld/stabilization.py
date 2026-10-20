"""Opt-in authored prerequisite executor. No Phase 9 learner or trained policy.

One world writer lease covers perception, reservations and native tick commits.
Control rows commit separately; recovery reconciles recorded native request IDs.
"""
import argparse
import copy
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import time

from . import storage, memory, cognition
from .lease import Lease
from .policy import _waypoint, _segment_clear
from .wire import dumps
from . import planning

VERSION='stabilization/4'


def source_id():
    root=Path(__file__).parent
    return hashlib.sha256(b''.join((root/name).read_bytes() for name in ('stabilization.py','planning.py','planning_model.py'))).hexdigest()


def _save(db,agent,state):
    payload=dumps(state)
    db.execute('INSERT OR REPLACE INTO stabilization_agents VALUES(?,?,?)',(agent,payload,storage.digest(payload)))


def _event(db,agent,tick,kind,data):
    number=db.execute('SELECT count(*) FROM stabilization_events').fetchone()[0]
    if number>=8192: raise ValueError('stabilization event quota reached')
    previous=db.execute('SELECT checksum FROM stabilization_events ORDER BY id DESC LIMIT 1').fetchone()
    payload=dumps(dict(agent=agent,tick=tick,kind=kind,data=data,previous=previous[0] if previous else None))
    if len(payload.encode())>65536: raise ValueError('stabilization audit payload bound')
    db.execute('INSERT INTO stabilization_events(payload,checksum) VALUES(?,?)',(payload,storage.digest(payload)))


def _load(db,agent):
    row=db.execute('SELECT payload,checksum FROM stabilization_meta').fetchone()
    if not row or storage.digest(row[0])!=row[1]: raise ValueError('stabilization metadata checksum')
    meta=json.loads(row[0])
    if meta['version']!=VERSION or meta['source_id']!=source_id(): raise ValueError('stabilization source/version mismatch')
    row=db.execute('SELECT payload,checksum FROM stabilization_agents WHERE agent=?',(agent,)).fetchone()
    if not row or storage.digest(row[0])!=row[1]: raise ValueError('stabilization agent checksum')
    return json.loads(row[0])


def verify_event_chain(db):
    previous=None
    for payload,checksum in db.execute('SELECT payload,checksum FROM stabilization_events ORDER BY id'):
        if storage.digest(payload)!=checksum or json.loads(payload)['previous']!=previous: raise ValueError('stabilization event chain')
        previous=checksum


def status(path,agent='agent-1'):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');storage._head(db);state=_load(db,agent)
        verify_event_chain(db)
        return state


def validate_options(model,call_limit):
    if type(model) is not bool:raise ValueError('model must be boolean')
    if type(call_limit) is not int or not 0<=call_limit<=16:raise ValueError('inference attempt bound')


def initialize(path,config,model=False,call_limit=2,knowledge_profile=None):
    """Validate the entire handoff before creating a new physical world."""
    from .config import validate
    validate_options(model,call_limit)
    config=copy.deepcopy(config);validate(config)
    if not config.get('agency',{}).get('bodies_enabled'):raise ValueError('body-enabled world required')
    if any(p.name.startswith('phase9-study') for p in (Path(path),*Path(path).parents)):
        raise ValueError('protected Phase 9 study; use a new stabilization world')
    config['agency']['policy']='none'
    storage.create(path,config,scripted=False,knowledge_profile=knowledge_profile)
    return attach(path,model=model,call_limit=call_limit)


def attach(path,agents=None,model=False,call_limit=2):
    """Explicit scheduler handoff, preserving bodies, native journal and own memories."""
    path=Path(path).resolve()
    if any(p.name.startswith('phase9-study') for p in (path,*path.parents)):
        raise ValueError('protected Phase 9 study; use a new stabilization world')
    validate_options(model,call_limit)
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');world,config,metadata,head=storage._head(db)
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone():
            raise ValueError('already attached; resume instead of resetting controller')
        ids=agents or [f'agent-{i+1}' for i in range(config['world']['population'])]
        for agent in ids: world.observe_batch([agent])
        if not config.get('agency',{}).get('bodies_enabled'): raise ValueError('body-enabled world required')
        old_policy=metadata['policy'];old_provider=config['cognition']['provider'];tick=int(world.snapshot()['tick'])
        # Never run the old scheduler alongside the executor. Native state is untouched.
        config['agency']['policy']='none';metadata['policy']='none'
        config['cognition']['provider']='disabled'
        metadata['config_hash']=storage.digest(dumps(config));metadata.pop('runtime_policy_state',None)
        metadata['stabilization_handoff']=dict(tick=tick,previous_policy=old_policy,previous_provider=old_provider,physical_head=head,version=VERSION,source_id=source_id())
        db.execute('UPDATE run SET config=?,metadata=? WHERE singleton=1',(dumps(config),dumps(metadata)))
        for agent,payload in db.execute('SELECT agent,payload FROM plans').fetchall():
            p=json.loads(payload)
            if p['status']=='pending':
                p['status']='preempted_by_explicit_stabilization_handoff'
                db.execute('UPDATE plans SET payload=? WHERE agent=?',(dumps(p),agent))
        memory.seal(db)
        db.execute('CREATE TABLE stabilization_meta(payload TEXT NOT NULL,checksum TEXT NOT NULL)')
        db.execute('CREATE TABLE stabilization_agents(agent TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)')
        db.execute('CREATE TABLE stabilization_events(id INTEGER PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)')
        payload=dumps(dict(version=VERSION,source_id=source_id(),initial_head=head,agents=ids))
        db.execute('INSERT INTO stabilization_meta VALUES(?,?)',(payload,storage.digest(payload)))
        for agent in ids:
            _save(db,agent,dict(agent=agent,model=model,call_limit=call_limit,calls=0,next_call_tick=tick,
                next_goal_tick=tick,sequence=0,goal=None,pending=None,navigation={},goals_completed=0,goals_blocked=0,
                submitted=0,authored_steps=0,fallback_goals=0,model_goals=0,model_latency_s=0.,last_tick=tick))
            _event(db,agent,tick,'explicit_handoff',dict(previous_policy=old_policy,model=model,authored_executor=True))
        db.commit()
    return status(path,ids[0])


def _need(o):
    b=o['own_state']['body']
    choices=[(b['thirst'],'drink'),(b['hunger'],'eat')]
    urgent=sorted((v,k) for v,k in choices if v>=.5)
    if urgent:return urgent[-1][1]
    return 'rest' if b['fatigue']>=.55 else None


def _context(o,view):
    c=cognition.context_for(o,view)
    # Add only quantities/geometry already present in this actor's permitted sight.
    c['perception']['own']['position_m']=o['own_state']['position_m']
    visible={e['entity_id']:e for e in o['visible_entities']}
    for e in c['perception']['visible']:
        source=visible[e['id']]
        e['position_m']=source['position_m']
        if 'mass_ug' in source:e['mass_ug']=source['mass_ug']
        e['within_reach']=math.dist(o['own_state']['position_m'],source['position_m'])<=1.5
    c['memories']=c['memories'][:1]
    for e in c['memories']:e['text']=e['text'][:100]
    return c


def _new_goal(s,o,kind,origin,raw=None):
    tick=int(o['tick']);s['sequence']+=1
    material='food' if kind=='eat' else 'water'
    reservoir=material+'_ingested_ug'
    g=dict(id=s['sequence'],kind=kind,origin=origin,created_tick=tick,phase='locate',steps=0,failures=0,
        initial_ingested_ug=int(o['own_state']['body'].get(reservoir,0)),target_mass_ug=200000000 if kind=='eat' else 300000000,
        raw=raw,target=None)
    s['goal']=g
    if origin=='model_selection':s['model_goals']+=1
    elif s['model']:s['fallback_goals']+=1
    return g


def _finish(db,s,o,outcome,reason):
    g=s['goal'];_event(db,s['agent'],int(o['tick']),'goal_'+outcome,g|dict(reason=reason))
    s['goals_completed' if outcome=='completed' else 'goals_blocked']+=1
    s['goal']=None;s['next_goal_tick']=int(o['tick'])+(10 if outcome!='completed' else 0)


def _action(s,o,kind,params=None,target=None,duration=1):
    s['sequence']+=1
    return dict(schema_version=1,run_id=o['run_id'],agent_id=s['agent'],request_id=f'stable-{s["agent"]}-{s["sequence"]}',
        observation_version=o['observation_version'],action_type=kind,target_ids=[] if target is None else [target],
        parameters=params or {},requested_duration=duration)


def _next(s,o,own_memory_ids=(),goal=None):
    g=goal if goal is not None else s['goal'];kind=g['kind'];own=o['own_state'];pos=own['position_m'];dt=o['dt_s']
    if kind in ('eat','drink'):
        material='food' if kind=='eat' else 'water'
        ingested=int(own['body'][material+'_ingested_ug'])-g['initial_ingested_ug']
        wanted=max(0,g['target_mass_ug']-ingested)
        duration=math.ceil((2 if kind=='eat' else 1)/dt)*dt
        # Consume real smaller portions too. Perishable materials share the food
        # ingestion reservoir; the goal still needs the full recorded mass delta.
        edible=['water'] if kind=='drink' else sorted(
            ('food','plant_food','eggs'),key=lambda m:(own.get('freshness_s',{}).get(m,float('inf')),m))
        for carried in edible:
            available=int(own['inventory_ug'].get(carried,'0'))
            freshness=own.get('freshness_s',{}).get(carried,float('inf'))
            if available<=0 or freshness<=duration+dt:continue
            amount=min(available,wanted)
            if amount<=0:return None,'ingestion_target_already_met'
            g['phase']='consume'
            params={'mass_kg':amount/1e9}
            if carried not in ('food','water'):params['material']=carried
            return _action(s,o,kind,params,duration=duration),None
        kinds=('food','forage') if kind=='eat' else ('water',)
        resources=sorted((e for e in o['visible_entities'] if e['kind'] in kinds and int(e['mass_ug'])>0),
                         key=lambda e:(math.dist(pos,e['position_m']),e['entity_id']))
        capacity=2000000000-int(own.get('carried_mass_ug',sum(int(v) for v in own['inventory_ug'].values())))
        if capacity<=0:return None,'capacity_blocked'
        if not resources:
            # No hidden resource map. Bounded perceived-space search only.
            g['phase']='search';g['target']=None
            bounds=o['world_bounds_m'];index=s['navigation'].get('search',0)%4
            goals=[(1.,1.),(bounds['width']-1,1.),(1.,bounds['height']-1),(bounds['width']-1,bounds['height']-1)]
            point=_waypoint(pos,goals[index],o['visible_entities'],bounds)
            s['navigation']['search']=index+1
            if not point or g['steps']>=4:return None,'no_observed_supply_after_bounded_search'
            g['steps']+=1
            return _action(s,o,'move',{'x_m':point[0],'y_m':point[1]},duration=max(dt,math.ceil(math.dist(pos,point)/dt)*dt)),None
        for resource in resources:
            g['target']=resource['entity_id']
            if math.dist(pos,resource['position_m'])<=1.45:
                amount=min(wanted,int(resource['mass_ug']),capacity)
                if amount<=0:continue
                g['phase']='gather'
                action='gather_plant' if resource['kind']=='forage' else 'gather'
                return _action(s,o,action,{'mass_kg':amount/1e9},resource['entity_id'],max(1,dt)),None
            # Stop short of the resource; native collision and reach remain authoritative.
            distance=math.dist(pos,resource['position_m'])
            radial=tuple(resource['position_m'][i]+(pos[i]-resource['position_m'][i])*1.1/distance for i in (0,1))
            candidates=[radial]+[(resource['position_m'][0]+1.1*math.cos(turn*math.tau/16),
                                  resource['position_m'][1]+1.1*math.sin(turn*math.tau/16)) for turn in range(16)]
            solids=[e for e in o['visible_entities'] if e['radius_m']>0]
            for goal in sorted(candidates,key=lambda p:math.dist(pos,p)):
                if not _segment_clear(goal,goal,solids):continue
                point=_waypoint(pos,goal,o['visible_entities'],o['world_bounds_m'])
                if point is not None:
                    g['phase']='approach';g['steps']+=1
                    return _action(s,o,'move',{'x_m':point[0],'y_m':point[1]},duration=max(dt,math.ceil(math.dist(pos,point)/dt)*dt)),None
        return None,'no_perceived_route'
    if kind=='rest':
        g['phase']='rest'
        return _action(s,o,'rest',duration=10),None
    # Other permitted model choices keep the existing compiler and native validator.
    _,req=cognition.compile_plan(g['raw'],o,own_memory_ids,s['sequence']+1)
    s['sequence']+=1;req['request_id']=f'stable-{s["agent"]}-{s["sequence"]}'
    g['phase']='direct'
    return req,None


def _task_request(db,s,o,config,provider):
    e=s['tasks'];t=e['active'];options,done,blocked=planning.choices(e,o)
    if done or blocked:
        planning.finish(db,s,o,'completed' if done else 'blocked',blocked or 'native_observable_goal_predicate')
        return None
    if options[0].get('delegate')=='eat':
        food=t.setdefault('food_goal',dict(kind='eat',target_mass_ug=round(t['params'].get('mass_kg',.2)*1e9),
                     initial_ingested_ug=t['initial_ingested_ug'],phase='locate',steps=0,target=None))
        req,reason=_next(s,o,goal=food)
        if reason:planning.finish(db,s,o,'blocked',reason);return None
        choice=dict(source='food_prerequisite',choice_origin='authored_execution')
    else:
        options=options[:3];selected=0;origin='authored_execution';error=None
        if t['mode']=='model_assisted' and len(options)>1:
            if e['calls']<4 and t['model_attempts']<1 and int(o['tick'])>=e['next_call_tick']:
                from .planning_model import PlanningModel
                context=dict(goal=t['goal'],inventory=o['own_state']['inventory_ug'],position=o['own_state']['position_m'],
                             operators=options,own_failures={c['source']:e['beliefs'][c['source']] for c in options if c['source'] in e['beliefs']})
                e['calls']+=1;t['model_attempts']+=1;e['next_call_tick']=int(o['tick'])+math.ceil(60/o['dt_s'])
                _event(db,s['agent'],int(o['tick']),'task_inference_reserved',context)
                _save(db,s['agent'],s);db.commit();started=time.perf_counter();raw=None;details={}
                try:
                    raw,details,_=cognition.bounded_call(provider or PlanningModel(),context,config['cognition'])
                    value=json.loads(raw)
                    if type(value) is not dict or set(value)!={'choice','reason'} or type(value['choice']) is not int or not 0<=value['choice']<len(options) or type(value['reason']) is not str or len(value['reason'])>120:
                        raise ValueError('task choice outside permitted operators')
                    selected=value['choice'];origin='model_operator_selection'
                except (ValueError,OSError,TimeoutError,EOFError,RuntimeError) as failure:
                    error=type(failure).__name__+': '+str(failure)[:200];origin='deterministic_fallback'
                elapsed=time.perf_counter()-started;e['model_latency_s']+=elapsed
                db.execute('BEGIN IMMEDIATE')
                _event(db,s['agent'],int(o['tick']),'task_inference_result',dict(raw=raw,selected=selected,origin=origin,error=error,latency_s=elapsed,details={k:v for k,v in details.items() if k!='prompt'}))
            else:origin='deterministic_fallback';error='task_inference_budget_or_interval'
        choice=options[selected]|dict(choice_origin=origin,fallback_reason=error)
        req=_action(s,o,choice['action'],choice['params'],choice['target'],choice['duration'])
    t['steps']+=1;t['pending_choice']=choice
    _event(db,s['agent'],int(o['tick']),'task_operator_selected',dict(task_id=t['id'],goal=t['goal'],choice=choice,request=req))
    return req


def step(path,agents=None,provider=None,fault=None,external=()):
    """One continuous native tick. Optional fault hooks test the cross-commit boundary."""
    with Lease(path):
        with closing(storage._connect(path,readonly=True)) as db:
            world,config,metadata,_=storage._head(db)
            if metadata['policy']!='none': raise ValueError('explicit scheduler handoff required')
            ids=agents or json.loads(db.execute('SELECT payload FROM stabilization_meta').fetchone()[0])['agents']
        requests=list(external)
        for agent in ids:
            o=storage.observe(path,[agent])[0];tick=int(o['tick'])
            with closing(storage._connect(path)) as db:
                db.execute('BEGIN IMMEDIATE');s=_load(db,agent);s['last_tick']=tick
                pending=s['pending']
                if pending:
                    rid=pending['request_id']
                    row=next((json.loads(r[0]) for r in db.execute('SELECT request FROM decisions') if json.loads(r[0]).get('request_id')==rid),None)
                    receipt=next((r for r in o['recent_action_results'] if r['request_id']==rid),None)
                    if row is None:
                        _event(db,agent,tick,'unsubmitted_reservation_discarded',pending)
                        s['pending']=None
                    elif row!=pending:raise ValueError('reserved request differs from native journal')
                    elif receipt is None:raise ValueError('reserved native receipt unavailable')
                    elif receipt['status'] in ('completed','failed','rejected'):
                        _event(db,agent,tick,'terminal_receipt',dict(request=pending,receipt=receipt))
                        s['pending']=None
                        if s.get('pending_owner')=='task':planning.record(s,pending,receipt,o)
                        elif s['goal']:
                            if receipt['status']!='completed':s['goal']['failures']+=1
                            elif s['goal']['kind'] not in ('eat','drink'):_finish(db,s,o,'completed','native_terminal_completion')
                own=o['own_state'];g=s['goal']
                task=s.get('tasks',{}).get('active')
                if task and not (s['pending'] and s.get('pending_owner')=='task') and tick-task['created_tick']>=math.ceil(360/o['dt_s']):
                    planning.finish(db,s,o,'blocked','task_deadline_including_survival_preemption')
                if g and g['kind'] in ('eat','drink'):
                    material='food' if g['kind']=='eat' else 'water'
                    if int(own['body'][material+'_ingested_ug'])-g['initial_ingested_ug']>=g['target_mass_ug']:
                        matched=next((r for r in o['recent_action_results'] if r['request_id']==g.get('consumption_request_id') and r['status']=='completed'),None)
                        _finish(db,s,o,'completed','native_ingested_reservoir_delta' if matched else 'external_native_consumption_not_executor_credit');g=None
                if g and (tick-g['created_tick']>=math.ceil(120/o['dt_s']) or g['steps']>=24 or g['failures']>=2):
                    _finish(db,s,o,'blocked','deadline_or_retry_limit');g=None
                if not own['alive'] or not own.get('present',True):
                    if s['goal']:_finish(db,s,o,'blocked','dead_or_absent')
                    if s.get('tasks',{}).get('active'):planning.finish(db,s,o,'blocked','dead_or_absent')
                    _save(db,agent,s);db.commit();continue
                if own['busy'] or s['pending']:
                    _save(db,agent,s);db.commit();continue
                if s.get('tasks',{}).get('active') and not s['goal'] and not _need(o):
                    req=_task_request(db,s,o,config,provider)
                    if req:
                        s['pending']=req;s['pending_owner']='task';s['submitted']+=1;s['authored_steps']+=1
                        _event(db,agent,tick,'request_reserved',dict(request=req,task_id=s['tasks']['active']['id'],executor='authored_hierarchical_executor',own_observation=o))
                        requests.append((tick,req))
                    _save(db,agent,s);db.commit();continue
                if not s['goal'] and tick>=s['next_goal_tick']:
                    need=_need(o);selected=None;raw=None;origin='authored_need_selection'
                    if s['model'] and s['calls']<s['call_limit'] and tick>=s['next_call_tick']:
                        view=memory.private_view(db,agent,'food water own actions');context=_context(o,view)
                        s['calls']+=1;s['next_call_tick']=tick+math.ceil(60/o['dt_s'])
                        _event(db,agent,tick,'inference_reserved',dict(attempt=s['calls'],context=context))
                        _save(db,agent,s);db.commit()
                        started=time.perf_counter();error=None;details={};valid_json=False;compiled=False
                        try:
                            raw,details,_=cognition.bounded_call(provider or cognition.LlamaCpp(),context,config['cognition'])
                            json.loads(raw);valid_json=True
                            plan,_=cognition.compile_plan(raw,o,[e['id'] for e in context['memories']],f'stable-{s["calls"]}')
                            compiled=True;selected=plan['intent'];origin='model_selection'
                            # Existing goal compiler is retained. A survival safety override is authored.
                            if need and selected not in ('eat','drink'):
                                selected=need;origin='deterministic_fallback';error='need_override_of_non_survival_choice'
                            if selected not in ('eat','drink','rest'):selected='direct'
                        except (ValueError,OSError,TimeoutError,EOFError,RuntimeError) as failure:
                            error=type(failure).__name__+': '+str(failure)[:240];selected=need;origin='deterministic_fallback'
                        elapsed=time.perf_counter()-started;s['model_latency_s']+=elapsed
                        db.execute('BEGIN IMMEDIATE')
                        _event(db,agent,tick,'inference_result',dict(raw=raw,valid_json=valid_json,compiled=compiled,selected=selected,
                            origin=origin,error=error,latency_s=elapsed,details={k:v for k,v in details.items() if k!='prompt'}))
                    else:
                        selected=need
                        if s['model']:origin='deterministic_fallback'
                    if selected:
                        g=_new_goal(s,o,selected,origin,raw)
                        _event(db,agent,tick,'goal_selected',g|dict(fallback_reason='budget_or_interval_or_need_override' if origin=='deterministic_fallback' else None))
                if s['goal']:
                    try:req,blocked=_next(s,o,[r[0] for r in db.execute('SELECT id FROM episodes WHERE agent=? ORDER BY id DESC LIMIT 64',(agent,))])
                    except ValueError as error:req,blocked=None,'compiler_invalidation: '+str(error)
                    if blocked:_finish(db,s,o,'blocked',blocked)
                    elif req:
                        if req['action_type'] in ('eat','drink'):s['goal']['consumption_request_id']=req['request_id']
                        s['pending']=req;s['pending_owner']='survival';s['submitted']+=1;s['authored_steps']+=1
                        _event(db,agent,tick,'request_reserved',dict(request=req,goal_id=s['goal']['id'],
                            goal_origin=s['goal']['origin'],executor='authored_prerequisite_executor',own_observation=o))
                        requests.append((tick,req))
                _save(db,agent,s);db.commit()
        if fault:fault('after_reservations')
        result=storage.advance(path,1,requests)
        if fault:fault('after_native_commit')
        return result


def run(path,seconds,wall_seconds=240,provider=None,agents=None,stop_requested=None):
    if type(seconds) not in (int,float) or not 0<seconds<=3600:raise ValueError('bounded duration required')
    if type(wall_seconds) not in (int,float) or not 0<wall_seconds<=3600:raise ValueError('bounded wall duration required')
    outcome='target_reached'
    with Lease(path):
        start=time.perf_counter();initial=storage.inspect(path);target=int(initial['tick'])+math.ceil(seconds/initial['dt_s'])
        while int(storage.inspect(path)['tick'])<target:
            if stop_requested and stop_requested():outcome='stopped';break
            if time.perf_counter()-start>=wall_seconds:outcome='wall_limit';break
            step(path,agents,provider)
    final=storage.inspect(path)
    return dict(status=outcome,initial_tick=initial['tick'],tick=final['tick'],simulated_s=(int(final['tick'])-int(initial['tick']))*final['dt_s'],
                wall_s=time.perf_counter()-start,state_hash=final['state_hash'],replay=storage.replay(path))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','attach','run','status'])
    p.add_argument('--db',type=Path,required=True);p.add_argument('--model',action='store_true');p.add_argument('--calls',type=int,default=2)
    p.add_argument('--config',type=Path,default=Path('config/survival.toml'))
    p.add_argument('--seconds',type=float,default=120);p.add_argument('--wall-seconds',type=float,default=240)
    p.add_argument('--endpoint',default='http://127.0.0.1:8081');args=p.parse_args()
    if args.command=='init':
        from .config import load
        result=initialize(args.db,load(args.config),model=args.model,call_limit=args.calls)
    elif args.command=='attach':result=attach(args.db,model=args.model,call_limit=args.calls)
    elif args.command=='status':result=status(args.db)
    else:result=run(args.db,args.seconds,args.wall_seconds,cognition.LlamaCpp(args.endpoint) if args.model else None)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
