"""Opt-in authored prerequisite executor. No Phase 9 learner or trained policy.

One world writer lease covers perception, reservations and native tick commits.
Control rows commit separately; recovery reconciles recorded native request IDs.
"""
import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

from . import storage, memory, cognition
from .lease import Lease
from .policy import _waypoint
from .wire import dumps

VERSION='stabilization/1'


def source_id(): return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


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


def status(path,agent='agent-1'):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');storage._head(db);state=_load(db,agent)
        previous=None
        for payload,checksum in db.execute('SELECT payload,checksum FROM stabilization_events ORDER BY id'):
            if storage.digest(payload)!=checksum or json.loads(payload)['previous']!=previous: raise ValueError('stabilization event chain')
            previous=checksum
        return state


def attach(path,agents=None,model=False,call_limit=2):
    """Explicit scheduler handoff, preserving bodies, native journal and own memories."""
    path=Path(path).resolve()
    if any(p.name.startswith('phase9-study') for p in (path,*path.parents)):
        raise ValueError('protected Phase 9 study; use a new stabilization world')
    if type(call_limit) is not int or not 0<=call_limit<=16: raise ValueError('inference attempt bound')
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');world,config,metadata,head=storage._head(db)
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone():
            raise ValueError('already attached; resume instead of resetting controller')
        ids=agents or [f'agent-{i+1}' for i in range(config['world']['population'])]
        for agent in ids: world.observe_batch([agent])
        if not config.get('agency',{}).get('bodies_enabled'): raise ValueError('body-enabled world required')
        old_policy=metadata['policy'];tick=int(world.snapshot()['tick'])
        # Never run the old scheduler alongside the executor. Native state is untouched.
        config['agency']['policy']='none';metadata['policy']='none'
        metadata['config_hash']=storage.digest(dumps(config));metadata.pop('runtime_policy_state',None)
        metadata['stabilization_handoff']=dict(tick=tick,previous_policy=old_policy,physical_head=head,version=VERSION,source_id=source_id())
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


def _next(s,o,own_memory_ids=()):
    g=s['goal'];kind=g['kind'];own=o['own_state'];pos=own['position_m'];dt=o['dt_s']
    if kind in ('eat','drink'):
        material='food' if kind=='eat' else 'water';wanted=g['target_mass_ug']
        held=int(own['inventory_ug'].get(material,'0'))
        if held>=wanted:
            g['phase']='consume'
            return _action(s,o,kind,{'mass_kg':wanted/1e9},duration=math.ceil((2 if kind=='eat' else 1)/dt)*dt),None
        resources=sorted((e for e in o['visible_entities'] if e['kind']==material and int(e['mass_ug'])>0),
                         key=lambda e:(math.dist(pos,e['position_m']),e['entity_id']))
        capacity=2000000000-sum(int(v) for v in own['inventory_ug'].values())
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
                amount=min(wanted-held,int(resource['mass_ug']),capacity)
                if amount<=0:continue
                g['phase']='gather'
                return _action(s,o,'gather',{'mass_kg':amount/1e9},resource['entity_id'],max(1,dt)),None
            # Stop short of the resource; native collision and reach remain authoritative.
            distance=math.dist(pos,resource['position_m'])
            goal=tuple(resource['position_m'][i]+(pos[i]-resource['position_m'][i])*1.1/distance for i in (0,1))
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
                        if s['goal']:
                            if receipt['status']!='completed':s['goal']['failures']+=1
                            elif s['goal']['kind'] not in ('eat','drink'):_finish(db,s,o,'completed','native_terminal_completion')
                own=o['own_state'];g=s['goal']
                if g and g['kind'] in ('eat','drink'):
                    material='food' if g['kind']=='eat' else 'water'
                    if int(own['body'][material+'_ingested_ug'])-g['initial_ingested_ug']>=g['target_mass_ug']:
                        _finish(db,s,o,'completed','native_ingested_reservoir_delta');g=None
                if g and (tick-g['created_tick']>=math.ceil(120/o['dt_s']) or g['steps']>=24 or g['failures']>=2):
                    _finish(db,s,o,'blocked','deadline_or_retry_limit');g=None
                if not own['alive'] or not own.get('present',True):
                    if s['goal']:_finish(db,s,o,'blocked','dead_or_absent')
                    _save(db,agent,s);db.commit();continue
                if own['busy'] or s['pending']:
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
                        s['pending']=req;s['submitted']+=1;s['authored_steps']+=1
                        _event(db,agent,tick,'request_reserved',dict(request=req,goal_id=s['goal']['id'],
                            goal_origin=s['goal']['origin'],executor='authored_prerequisite_executor',own_observation=o))
                        requests.append((tick,req))
                _save(db,agent,s);db.commit()
        if fault:fault('after_reservations')
        result=storage.advance(path,1,requests)
        if fault:fault('after_native_commit')
        return result


def run(path,seconds,wall_seconds=240,provider=None,agents=None):
    if type(seconds) not in (int,float) or not 0<seconds<=3600:raise ValueError('bounded duration required')
    start=time.perf_counter();initial=storage.inspect(path);target=int(initial['tick'])+math.ceil(seconds/initial['dt_s'])
    outcome='target_reached'
    while int(storage.inspect(path)['tick'])<target:
        if time.perf_counter()-start>=wall_seconds:outcome='wall_limit';break
        step(path,agents,provider)
    final=storage.inspect(path)
    return dict(status=outcome,initial_tick=initial['tick'],tick=final['tick'],simulated_s=(int(final['tick'])-int(initial['tick']))*final['dt_s'],
                wall_s=time.perf_counter()-start,state_hash=final['state_hash'],replay=storage.replay(path))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','attach','run','status'])
    p.add_argument('--db',type=Path,required=True);p.add_argument('--model',action='store_true');p.add_argument('--calls',type=int,default=2)
    p.add_argument('--seconds',type=float,default=120);p.add_argument('--wall-seconds',type=float,default=240)
    p.add_argument('--endpoint',default='http://127.0.0.1:8081');args=p.parse_args()
    if args.command=='init':
        from .config import load
        cfg=load(Path(__file__).resolve().parents[1]/'config/survival.toml');cfg['agency']['policy']='none'
        storage.create(args.db,cfg,scripted=False)
    if args.command in ('init','attach'):result=attach(args.db,model=args.model,call_limit=args.calls)
    elif args.command=='status':result=status(args.db)
    else:result=run(args.db,args.seconds,args.wall_seconds,cognition.LlamaCpp(args.endpoint) if args.model else None)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
