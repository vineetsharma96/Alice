"""Bounded authored HTN operators, using only permitted actor data.

Recipes here are explicitly assigned procedural templates, never an automatic
read of the privileged native recipe registry. Physical effects stay native.
"""
import math
import heapq
from contextlib import closing

from . import memory, storage
from .lease import Lease
from .policy import _segment_clear, _waypoint

GOALS=('obtain_food','obtain_wood','craft_tool','make_planks','build_trough',
       'provide_water','tend_animal','inspect_problem','rest','build_pen','teach_procedure','feed_animal')
SUPPORTED=set(GOALS)-{'teach_procedure'}


def deadline(task):return 900 if task['goal']=='build_pen' else 360


def assignment(goal,params):
    if goal not in GOALS:raise ValueError('unknown hierarchical goal')
    if type(params) is not dict or set(params)-{'target','mass_kg','position_m','lesson_episode_id'}:
        raise ValueError('unknown task parameters')
    if 'target' in params and (type(params['target']) is not str or not 1<=len(params['target'])<=64):
        raise ValueError('task target must be a bounded ID')
    if 'mass_kg' in params:
        v=params['mass_kg']
        if type(v) not in (int,float) or not math.isfinite(v) or not .001<=v<=1 or abs(v*1e9-round(v*1e9))>1e-5:
            raise ValueError('task mass must be .001..1 kg with native resolution')
    if 'position_m' in params:
        p=params['position_m']
        if type(p) is not list or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):
            raise ValueError('construction position must be two finite numbers')
    if goal in ('tend_animal','inspect_problem','feed_animal') and 'target' not in params:raise ValueError('target required')
    if 'lesson_episode_id' in params and (goal!='feed_animal' or type(params['lesson_episode_id']) is not int or params['lesson_episode_id']<1):
        raise ValueError('own lesson id is supported only for assigned feeding')


def assign(path,agent,goal,params=None,mode='adaptive'):
    """Explicit external task/procedure assignment; never physical mutation."""
    from . import stabilization as stable
    params={} if params is None else params;assignment(goal,params)
    if mode not in ('authored','episodic_only','adaptive','model_assisted'):raise ValueError('unknown task mode')
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');world,config,_,_=storage._head(db);s=stable._load(db,agent)
        o=world.observe_batch([agent])[0]
        if s['model']:raise ValueError('E task controller requires legacy survival model calls disabled')
        if s.get('tasks',{}).get('active'):raise ValueError('task already active; finish or cancel explicitly')
        if not o['own_state']['alive'] or not o['own_state'].get('present',True):raise ValueError('inhabitant is dead or absent')
        e=s.setdefault('tasks',dict(active=None,history=[],procedures={},beliefs={},calls=0,model_latency_s=0.,next_call_tick=0))
        s['sequence']+=1;tick=int(o['tick'])
        prior=e['procedures'].get(goal) if mode in ('adaptive','model_assisted') else None
        if prior:
            row=db.execute("SELECT payload FROM episodes WHERE id=? AND agent=? AND kind='verified_procedure'",(prior['episode_id'],agent)).fetchone()
            if not row or storage.loads(row[0])['goal']!=goal:raise ValueError('own procedure evidence unavailable; no implicit provenance repair')
        t=dict(id=s['sequence'],goal=goal,params=dict(params),mode=mode,created_tick=tick,
               stage='decompose',steps=0,failures=0,search=0,receipts=[],delivered_ug=0,
               report=None,report_tick=None,care_effects=0,pending_choice=None,model_attempts=0,
               origin='own_verified_procedure_reuse' if prior else 'operator_assigned_authored_procedure',
               procedure_source=prior['episode_id'] if prior else None,
               initial_ingested_ug=int(o['own_state']['body']['food_ingested_ug']))
        if params.get('lesson_episode_id'):
            from . import care
            from .config import episodic_enabled
            if not episodic_enabled(config):raise ValueError('care lesson requires episodic retention')
            claim,record=care.lesson(db,agent,params['lesson_episode_id'])
            t.update(lesson_episode_id=params['lesson_episode_id'],lesson_source_id=record['source_id'],care_claim=claim,
                     knowledge_origin='own_accessed_external_claim',execution_origin='authored_assigned_care_executor')
        e['active']=t
        stable._event(db,agent,tick,'task_assigned',t)
        stable._save(db,agent,s);db.commit()
    return stable.status(path,agent)['tasks']


def cancel(path,agent):
    from . import stabilization as stable
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');world,_,_,_=storage._head(db);s=stable._load(db,agent)
        e=s.get('tasks');o=world.observe_batch([agent])[0]
        if not e or not e['active']:raise ValueError('no active task')
        # Cancellation is a durable request, resolved after the in-flight native
        # receipt. Neither its committed effects nor its evidence can be erased.
        if s['pending'] and s.get('pending_owner')=='task':
            e['active']['cancel_requested']=True
            stable._event(db,agent,int(o['tick']),'task_cancel_requested',dict(task_id=e['active']['id']))
        else:finish(db,s,o,'blocked','explicit_operator_cancellation')
        stable._save(db,agent,s);db.commit()
    return stable.status(path,agent)['tasks']


def finish(db,s,o,outcome,reason):
    from . import stabilization as stable
    e=s['tasks'];t=e['active'];tick=int(o['tick'])
    proof=[r['request_id'] for r in t['receipts'] if r['status']=='completed']
    terminal_kind={'obtain_food':'eat','obtain_wood':'collect_wood','craft_tool':'craft','make_planks':'craft',
                   'build_trough':'work_construction','provide_water':'fill_trough','tend_animal':'observe_animal',
                   'inspect_problem':'inspect','rest':'rest','build_pen':'work_construction','feed_animal':'offer_feed'}.get(t['goal'])
    earned=any(r['status']=='completed' and r['action']==terminal_kind for r in t['receipts'])
    summary={k:t[k] for k in ('id','goal','mode','origin','procedure_source','created_tick','steps','failures','delivered_ug')}
    summary.update(outcome=outcome,reason=reason,completed_tick=tick,evidence=proof,executor_goal_credit=outcome=='completed' and earned)
    summary['native_failures']=[r for r in t['receipts'] if r['status']!='completed']
    for key in ('lesson_episode_id','lesson_source_id','knowledge_origin','execution_origin','enclosure_ids','enclosure_observations'):
        if key in t:summary[key]=t[key]
    if outcome=='completed' and not earned:summary['reason']='already_satisfied_or_external_effect_no_procedure_credit'
    if outcome=='completed' and earned and t['mode'] in ('adaptive','model_assisted'):
        source=f'procedure:{t["id"]}'
        memory.episode(db,s['agent'],source,tick,'verified_procedure',dict(
            text='Authored procedure achieved a native-observable goal: '+t['goal'],
            request_ids=proof,source_type='own_native_receipts',authored_decomposition=True,
            goal=t['goal'],primitive_sequence=[r['action'] for r in t['receipts'] if r['status']=='completed'],
            reusable_method='authored_htn:'+t['goal'],skill_granted=False))
        episode=db.execute('SELECT id FROM episodes WHERE agent=? AND source=?',(s['agent'],source)).fetchone()[0]
        e['procedures'][t['goal']]=dict(episode_id=episode,successes=e['procedures'].get(t['goal'],{}).get('successes',0)+1,
                                       confidence='verified_in_recorded_context_only')
        summary['procedure_episode_id']=episode;memory.seal(db)
    stable._event(db,s['agent'],tick,'task_'+outcome,summary)
    e['history']=(e['history']+[summary])[-16:];e['active']=None


def record(s,request,receipt,o):
    """Called only after coordinator matches pending request to durable journal."""
    e=s['tasks'];t=e['active']
    if not t:raise ValueError('task receipt has no accountable task')
    choice=t.get('pending_choice') or {};key=choice.get('source',request['action_type'])
    row=dict(request_id=request['request_id'],action=request['action_type'],status=receipt['status'],
             error=receipt['error_code'],event_refs=receipt['event_refs'],tick=int(o['tick']),source=key,
             description=receipt.get('observable_effects',{}).get('description','')[:300])
    t['receipts']=(t['receipts']+[row])[-64:];t['pending_choice']=None
    if receipt['status']!='completed':
        t['failures']+=1
        if len(e['beliefs'])>=64 and key not in e['beliefs']:del e['beliefs'][next(iter(e['beliefs']))]
        b=e['beliefs'].setdefault(key,dict(failures=0,successes=0,evidence=[]))
        b['failures']+=1;b['last_error']=receipt['error_code'];b['last_tick']=int(o['tick'])
        b['evidence']=(b['evidence']+[row['request_id']])[-4:]
    else:
        if key in e['beliefs']:e['beliefs'][key]['successes']+=1
        if request['action_type']=='fill_trough':t['delivered_ug']+=round(request['parameters']['mass_kg']*1e9);t['care_effects']+=1
        if request['action_type']=='offer_feed':t['care_effects']+=1
        if request['action_type']=='begin_construction':
            t['construction_id']=row['description'].rsplit(':entity=',1)[-1]
            if key.startswith('pen:'):t.setdefault('enclosure_ids',{})[key[4:]]=t['construction_id']
        if request['action_type']=='work_construction':t['construction_id']=request['target_ids'][0]
        if request['action_type']=='observe_animal':t['report']=row['description'];t['report_tick']=int(o['tick'])
        elif request['action_type'] in ('offer_feed','fill_trough'):t['report']=None


def _option(kind,params=None,target=None,duration=1,source=None):
    return dict(action=kind,params=params or {},target=target,duration=duration,source=source or f'{kind}:{target or "self"}')


def _route(o,goal):
    """Reuse coarse navigation first; half-metre fallback for tight clearance."""
    start=o['own_state']['position_m'];visible=o['visible_entities'];bounds=o['world_bounds_m']
    point=_waypoint(start,goal,visible,bounds)
    if point:return point
    solids=[x for x in visible if x['radius_m']>0]
    origin=tuple(round(v*2) for v in start)
    queue=[(math.dist(start,goal),0,origin)];costs={origin:0};first={origin:None}
    for _ in range(512):
        if not queue:break
        _,cost,node=heapq.heappop(queue)
        if cost!=costs[node]:continue
        current=start if node==origin else tuple(v/2 for v in node)
        if math.dist(current,goal)<.8 and _segment_clear(current,goal,solids):return first[node] or goal
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)):
            nxt=(node[0]+dx,node[1]+dy);p=tuple(v/2 for v in nxt)
            if not .3<=p[0]<=bounds['width']-.3 or not .3<=p[1]<=bounds['height']-.3 or math.dist(start,p)>8:continue
            if not _segment_clear(current,p,solids):continue
            total=cost+math.dist(current,p)
            if total>=costs.get(nxt,float('inf')):continue
            costs[nxt]=total;first[nxt]=first[node] or p
            heapq.heappush(queue,(total+math.dist(p,goal),total,nxt))
    # A visibility graph around perceived exclusion circles covers narrow
    # clearances that neither regular grid represents, including region edges.
    nodes=[start,goal]
    for solid in sorted(solids,key=lambda x:math.dist(start,x['position_m']))[:16]:
        radius=(solid['radius_m']+.25+.04)/math.cos(math.pi/12)+.015
        for i in range(12):
            q=solid['position_m'];p=(q[0]+radius*math.cos(i*math.tau/12),q[1]+radius*math.sin(i*math.tau/12))
            if .3<=p[0]<=bounds['width']-.3 and .3<=p[1]<=bounds['height']-.3 and _segment_clear(p,p,solids):nodes.append(p)
    queue=[(math.dist(start,goal),0,0)];costs={0:0};first={0:None};edges=0
    while queue and edges<16384:
        _,cost,index=heapq.heappop(queue)
        if cost!=costs[index]:continue
        if index==1:return first[index]
        for other,p in enumerate(nodes):
            if other==index:continue
            edges+=1
            if edges>16384:break
            new=cost+math.dist(nodes[index],p)
            if new>=costs.get(other,float('inf')) or not _segment_clear(nodes[index],p,solids):continue
            costs[other]=new;first[other]=first[index] or p
            heapq.heappush(queue,(new+math.dist(p,goal),new,other))
    return None


def _approach(o,target,operation):
    pos=o['own_state']['position_m'];q=target['position_m']
    if math.dist(pos,q)<=1.4:return operation
    solids=[e for e in o['visible_entities'] if e['radius_m']>0]
    def visible_from(point):
        dx,dy=q[0]-point[0],q[1]-point[1];length=dx*dx+dy*dy
        for solid in solids:
            if solid.get('entity_id')==target.get('entity_id'):continue
            x,y=solid['position_m'];part=0 if not length else max(0,min(1,((x-point[0])*dx+(y-point[1])*dy)/length))
            if math.hypot(point[0]+part*dx-x,point[1]+part*dy-y)<solid['radius_m']+.01:return False
        return True
    route_memory=o.get('_route_memory',{})
    key=operation['source']+':'+str(tuple(q))
    cached=route_memory.get(key)
    if cached and _segment_clear(cached,cached,solids) and visible_from(cached):
        point=_route(o,cached)
        if point and math.dist(pos,point)>.05:
            return _option('move',{'x_m':point[0],'y_m':point[1]},duration=max(o['dt_s'],math.ceil(math.dist(pos,point)/o['dt_s'])*o['dt_s']),source=operation['source'])
    route_memory.pop(key,None)
    angle=math.atan2(pos[1]-q[1],pos[0]-q[0])
    goals=[(q[0]+radius*math.cos(angle+i*math.tau/16),q[1]+radius*math.sin(angle+i*math.tau/16)) for radius in (1.1,.8,1.35) for i in range(16)]
    for goal in sorted(goals,key=lambda p:math.dist(pos,p)):
        if not _segment_clear(goal,goal,solids) or not visible_from(goal):continue
        point=_route(o,goal)
        if point and math.dist(pos,point)>.05:
            route_memory[key]=goal
            while len(route_memory)>32:del route_memory[next(iter(route_memory))]
            return _option('move',{'x_m':point[0],'y_m':point[1]},duration=max(o['dt_s'],math.ceil(math.dist(pos,point)/o['dt_s'])*o['dt_s']),source=operation['source'])
    return None


def _rank(e,t,o,options):
    by_id={x['entity_id']:x for x in o['visible_entities']}
    def score(c):
        belief=e['beliefs'].get(c['source'],{}) if t['mode'] in ('adaptive','model_assisted') else {}
        penalty=max(0,belief.get('failures',0)-belief.get('successes',0))
        target=by_id.get(c.get('target'))
        return penalty,math.dist(o['own_state']['position_m'],target['position_m']) if target else 0,c['source']
    # Rank before approach expansion so source distance is retained for moves.
    return sorted(options,key=score)


def _resources(e,t,o,material,amount):
    if t.get('resource_search_for')!=material:
        t.update(resource_search_for=material,search=0,search_steps=0)
    own=o['own_state'];capacity=2000000000-int(own['carried_mass_ug'])
    if capacity<=0:return [],'carrying_capacity_blocked'
    options=[]
    for target in o['visible_entities']:
        if target['kind']!=material or int(target.get('mass_ug',0))<=0:continue
        n=min(amount,int(target['mass_ug']),capacity)
        action='gather' if material in ('food','water') else 'gather_plant' if material=='forage' else 'collect_wood'
        params={'mass_kg':n/1e9}
        if action=='collect_wood':params['material']=material
        options.append(_option(action,params,target['entity_id'],source=f'{material}:{target["entity_id"]}'))
    ranked=_rank(e,t,o,options)
    ready=[_approach(o,next(x for x in o['visible_entities'] if x['entity_id']==c['target']),c) for c in ranked]
    ready=[c for c in ready if c]
    if ready:return ready,None
    if material in ('wood','fiber'):
        trees=[x for x in o['visible_entities'] if x['kind']=='tree' and x.get('stage')!='stump' and int(x.get('mass_ug',0))>=500000000]
        axe=next((x for x in own.get('tools',[]) if x.get('recipe_id')=='crude_axe' and x.get('durability',0)>0),None)
        choices=[_option('fell_tree',{'tool_id':axe['entity_id']},x['entity_id'],duration=5,source=f'fell:{x["entity_id"]}')
                 if axe and material=='wood' else _option('harvest_branch',{'mass_kg':.5},x['entity_id'],source=f'harvest:{x["entity_id"]}') for x in trees]
        ready=[]
        for choice in _rank(e,t,o,choices):
            target=next(x for x in trees if x['entity_id']==choice['target']);c=_approach(o,target,choice)
            if c:ready.append(c)
        if ready:return ready,None
    remembered=remembered_route(o,t.get('known_resource_sites',{}),(material,))
    if remembered:return [remembered],None
    return [],'no_observed_accessible_'+material


def remembered_route(o,sites,kinds,navigation=None):
    """Approach a last observed location, then demand fresh visibility to gather."""
    visible={x['entity_id'] for x in o['visible_entities']}
    if navigation is not None:o=dict(o,_route_memory=navigation)
    for ident,site in sorted(list(sites.items()),key=lambda row:math.dist(o['own_state']['position_m'],row[1]['position_m'])):
        if site['kind'] not in kinds or ident in visible:continue
        if math.dist(o['own_state']['position_m'],site['position_m'])<=1.4:
            sites.pop(ident,None);continue
        choice=_approach(o,site,_option('inspect',target=ident,source='own_remembered_source:'+ident))
        if choice and choice['action']=='move':return choice
    return None


def _axe(e,t,o):
    usable=next((x for x in o['own_state'].get('tools',[]) if x['kind']=='tool' and x['recipe_id']=='crude_axe' and x['durability']>0),None)
    if usable:return usable['entity_id'],[],None
    for material,n in (('wood',450000000),('fiber',50000000),('stone',200000000)):
        missing=n-int(o['own_state']['inventory_ug'].get(material,0))
        if missing>0:
            options,reason=_resources(e,t,o,material,missing);return None,options,reason
    return None,[_option('craft',{'recipe_id':'crude_axe'},duration=4)],None


def _planks(e,t,o):
    tool,options,reason=_axe(e,t,o)
    if not tool:return options,reason
    missing=1000000000-int(o['own_state']['inventory_ug'].get('wood',0))
    shortage=int(o['own_state']['carried_mass_ug'])+missing-2000000000
    if missing>0 and shortage>0:
        from .enclosure import store_offcuts
        return store_offcuts(e,t,o,shortage)
    if missing>0:return _resources(e,t,o,'wood',missing)
    return [_option('craft',{'recipe_id':'planks','tool_id':tool},duration=3)],None


def _build(e,t,o):
    position=t['params'].get('position_m')
    sites=[x for x in o['visible_entities'] if x['kind']=='construction' and x.get('recipe_id')=='trough' and x.get('owner_id')==o['agent_id']]
    if sites:
        site=sites[0];c=_approach(o,site,_option('work_construction',target=site['entity_id'],duration=max(1,8-site['work_s'])))
        return ([c],None) if c else ([], 'construction_inaccessible')
    if int(o['own_state']['inventory_ug'].get('plank',0))<800000000:return _planks(e,t,o)
    if position:
        c,ready=placement_stance(o,position,'trough_site_approach')
        if not ready:return ([c],None) if c else ([], 'assigned_construction_site_inaccessible')
    pos=o['own_state']['position_m'];bounds=o['world_bounds_m']
    points=[position] if position else [[pos[0]+1.1*math.cos(i*math.tau/16),pos[1]+1.1*math.sin(i*math.tau/16)] for i in range(16)]
    for point in points:
        if not .5<=point[0]<=bounds['width']-.5 or not .5<=point[1]<=bounds['height']-.5:continue
        if math.dist(pos,point)>1.4:continue
        if any(math.dist(point,x['position_m'])<.5+x['radius_m']+.01 for x in o['visible_entities'] if x['radius_m']>0):continue
        if not _segment_clear(pos,point,[x for x in o['visible_entities'] if x['radius_m']>0]):continue
        return [_option('begin_construction',{'recipe_id':'trough','x_m':point[0],'y_m':point[1]})],None
    return [],'no_permitted_construction_site'


def placement_stance(o,point,source):
    """An unbuilt site is not yet a solid, but the builder must clear its footprint."""
    pos=o['own_state']['position_m'];distance=math.dist(pos,point)
    if .8<=distance<=1.4:return None,True
    if distance>1.4:
        c=_approach(o,{'position_m':point,'radius_m':0},_option('inspect',target='unbuilt-site',source=source))
        return (c if c and c['action']=='move' else None),False
    solids=[x for x in o['visible_entities'] if x['radius_m']>0];bounds=o['world_bounds_m']
    angle=math.atan2(pos[1]-point[1],pos[0]-point[0])
    for i in range(16):
        goal=[point[0]+1.1*math.cos(angle+i*math.tau/16),point[1]+1.1*math.sin(angle+i*math.tau/16)]
        if not .3<=goal[0]<=bounds['width']-.3 or not .3<=goal[1]<=bounds['height']-.3:continue
        if not _segment_clear(pos,goal,solids):continue
        return _option('move',{'x_m':goal[0],'y_m':goal[1]},duration=max(o['dt_s'],math.ceil(math.dist(pos,goal)/o['dt_s'])*o['dt_s']),source=source),False
    return None,False


def choices(e,o):
    """Return feasible candidate primitives, a success predicate, or a reason."""
    t=e['active'];goal=t['goal'];own=o['own_state'];visible=o['visible_entities']
    o=dict(o,_route_memory=t.setdefault('approach_memory',{}))
    if t.get('cancel_requested'):return [],False,'explicit_operator_cancellation_after_native_receipt'
    if goal not in SUPPORTED:return [],False,'unsupported_task:'+goal
    if t['steps']>=(192 if goal=='build_pen' else 64) or t['failures']>=4 or int(o['tick'])-t['created_tick']>=math.ceil(deadline(t)/o['dt_s']):
        return [],False,'task_deadline_or_retry_bound'
    t['stage']=goal
    if goal=='build_pen':
        from .enclosure import choices as pen_choices
        return pen_choices(e,t,o)
    if goal=='feed_animal':
        if t['care_effects']>0:return [],True,None
        if t['failures']>0:return [],False,'native_care_test_failed'
        target=next((x for x in visible if x['entity_id']==t['params']['target'] and x['kind']=='animal'),None)
        if not target:return _search(t,o,'assigned_animal_not_observed')
        material=t.get('care_claim',{}).get('material','food')
        amount=round(t['params'].get('mass_kg',.025)*1e9)
        if amount>400000000:return [],False,'feeding_amount_out_of_bounds'
        held=int(own['inventory_ug'].get(material,0))
        if held<amount:
            options,reason=_resources(e,t,o,material,amount-held)
            if not options and reason and reason.startswith('no_observed_accessible_'):return _search(t,o,reason)
            return options,False,reason
        c=_approach(o,target,_option('offer_feed',{'material':material,'mass_kg':amount/1e9},target['entity_id']))
        return ([c],False,None) if c else ([],False,'animal_inaccessible')
    if goal=='obtain_food':
        if int(own['body']['food_ingested_ug'])-t['initial_ingested_ug']>=round(t['params'].get('mass_kg',.2)*1e9):return [],True,None
        return [dict(delegate='eat')],False,None
    if goal=='obtain_wood':
        n=round(t['params'].get('mass_kg',.5)*1e9)-int(own['inventory_ug'].get('wood',0))
        if n<=0:return [],True,None
        options,reason=_resources(e,t,o,'wood',n)
    elif goal=='craft_tool':
        tool,options,reason=_axe(e,t,o)
        if tool:return [],True,None
    elif goal=='make_planks':
        if int(own['inventory_ug'].get('plank',0))>=800000000:return [],True,None
        options,reason=_planks(e,t,o)
    elif goal in ('build_trough','provide_water'):
        target=next((x for x in visible if x['kind']=='trough' and
                     (x['entity_id']==t.get('construction_id') if goal=='build_trough' else
                      not t['params'].get('target') or x['entity_id']==t['params']['target'])),None)
        if goal=='build_trough' and target:return [],True,None
        amount=round(t['params'].get('mass_kg',.3)*1e9)-t['delivered_ug']
        if goal=='provide_water' and amount<=0:return [],True,None
        if not target:
            if t['params'].get('target'):return [],False,'assigned_target_not_observed'
            options,reason=_build(e,t,o)
        else:
            held=int(own['inventory_ug'].get('water',0))
            if held<amount:options,reason=_resources(e,t,o,'water',amount-held)
            else:
                c=_approach(o,target,_option('fill_trough',{'material':'water','mass_kg':amount/1e9},target['entity_id']))
                options,reason=([c],None) if c else ([], 'trough_inaccessible')
    elif goal=='tend_animal':
        target=next((x for x in visible if x['entity_id']==t['params']['target'] and x['kind']=='animal'),None)
        if not target:return [],False,'assigned_animal_not_observed'
        report=t['report']
        if not report or int(o['tick'])-t['report_tick']>math.ceil(10/o['dt_s']):
            return [_option('observe_animal',target=target['entity_id'],duration=max(.2,o['dt_s']))],False,None
        if ':hunger=low:' in report and ':thirst=low:' in report:return [],True,None
        if ':hunger=high:' in report:
            edible=next((m for m in ('plant_food','eggs','food') if int(own['inventory_ug'].get(m,0))>=100000000 and own.get('freshness_s',{}).get(m,999)>1+o['dt_s']),None)
            if not edible:options,reason=_resources(e,t,o,'food',100000000)
            else:
                c=_approach(o,target,_option('offer_feed',{'material':edible,'mass_kg':.1},target['entity_id']))
                options,reason=([c],None) if c else ([], 'animal_inaccessible')
        else:
            trough=next((x for x in visible if x['kind']=='trough' and math.dist(x['position_m'],target['position_m'])<=3),None)
            if not trough:return [],False,'no_observed_animal_water_access'
            if t['delivered_ug']>=300000000:
                t['report']=None;return [_option('rest',duration=1)],False,None
            held=int(own['inventory_ug'].get('water',0))
            if held<300000000:options,reason=_resources(e,t,o,'water',300000000-held)
            else:
                c=_approach(o,trough,_option('fill_trough',{'material':'water','mass_kg':.3},trough['entity_id']))
                options,reason=([c],None) if c else ([], 'trough_inaccessible')
    elif goal in ('inspect_problem','rest'):
        kind='inspect' if goal=='inspect_problem' else 'rest'
        if any(r['status']=='completed' and r['action']==kind for r in t['receipts']):return [],True,None
        if kind=='inspect' and not any(x['entity_id']==t['params']['target'] for x in visible):return [],False,'assigned_target_not_observed'
        return [_option(kind,target=t['params'].get('target'),duration=2)],False,None
    else:raise ValueError('task dispatch incomplete')
    if options:return options,False,None
    # Only missing supplies trigger bounded perceived-space exploration.
    if reason and reason.startswith('no_observed_accessible_'):return _search(t,o,reason)
    return [],False,reason or 'no_feasible_operator'


def _search(t,o,reason):
    if t['search']<4 and t.get('search_steps',0)<12:
        b=o['world_bounds_m'];goals=[(1,1),(b['width']-1,1),(1,b['height']-1),(b['width']-1,b['height']-1)]
        while t['search']<4:
            if math.dist(o['own_state']['position_m'],goals[t['search']])<.5:t['search']+=1;continue
            point=_route(o,goals[t['search']])
            if point and math.dist(point,o['own_state']['position_m'])>.05:
                t['search_steps']=t.get('search_steps',0)+1
                d=math.dist(point,o['own_state']['position_m']);return [_option('move',{'x_m':point[0],'y_m':point[1]},duration=max(o['dt_s'],math.ceil(d/o['dt_s'])*o['dt_s']),source='bounded_local_search')],False,None
            t['search']+=1
    return [],False,reason or 'no_feasible_operator'
