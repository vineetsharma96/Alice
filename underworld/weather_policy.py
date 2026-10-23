"""Bounded authored weather/survival goals using ONLY own observations and memory."""
import hashlib
import math

from . import planning


def state():
    return dict(serial=0, memory={}, goal=None, failures=0, build_steps=0, blocked_until=0,
                exposure_latch=False, search=0, completed=[], decisions=0, preemptions=0,
                fallback=0, assigned=None, last=None, seek_steps=0, need=None, sheltered_since=None)


def option(action='rest', parameters=None, target=None, duration=5, goal='reduce_exposure'):
    return dict(action=action, parameters=parameters or {}, targets=[target] if target else [],
                duration=duration, goal=goal, origin='authored_weather_baseline')


def memory(o, s):
    tick = int(o['tick'])
    for e in o['visible_entities']:
        if e['kind'] in ('food', 'water', 'tree', 'wood', 'fiber', 'lean_to', 'construction'):
            s['memory'][e['entity_id']] = dict(entity=e, tick=tick, source='own_native_observation',
                                             observer=o['agent_id'])
    while len(s['memory']) > 48:
        del s['memory'][min(s['memory'], key=lambda k:s['memory'][k]['tick'])]
    if any(r['observer']!=o['agent_id'] or r['source']!='own_native_observation' or r['tick']>tick for r in s['memory'].values()):
        raise ValueError('Foreign/future weather memory refused')
    return [s['memory'][key]['entity'] for key in sorted(s['memory']) if (tick-s['memory'][key]['tick'])*o['dt_s'] <= 600]


def approach(o, target, choice):
    # Pure existing local route machinery. It receives no database or global map.
    original = planning._option(choice['action'], choice['parameters'], choice['targets'][0] if choice['targets'] else None,
                                duration=choice['duration'], source='weather_authored')
    routed = planning._approach(o, target, original)
    if routed is None:return option(goal='blocked_route_'+choice['goal'])
    if routed['action'] == 'move':
        p = routed['params']; pos = o['own_state']['position_m']; destination = [p['x_m'], p['y_m']]
        length = math.dist(pos, destination)
        if length > 3:destination = [pos[i]+(destination[i]-pos[i])*3/length for i in range(2)]
        return option('move', dict(x_m=destination[0], y_m=destination[1]), duration=max(o['dt_s'], math.ceil(min(length,3)/o['dt_s'])*o['dt_s']), goal=choice['goal'])
    return choice


def go(o, position, goal):
    point = planning._route(o, position)
    if point is None:return option(goal=goal)
    pos=o['own_state']['position_m']; length=math.dist(pos, point)
    if length>3:point=[pos[i]+(point[i]-pos[i])*3/length for i in range(2)]
    return option('move', dict(x_m=point[0],y_m=point[1]), duration=max(o['dt_s'],math.ceil(min(length,3)/o['dt_s'])*o['dt_s']),goal=goal)


def supplies(o, known, material, threshold=.05):
    if int(o['own_state']['inventory_ug'].get(material,0)) >= round(threshold*1e9):
        return option('eat' if material=='food' else 'drink',dict(mass_kg=.05),duration=2 if material=='food' else 1,goal='urgent_'+material)
    targets=[e for e in known if e['kind']==material and int(e['mass_ug'])>=50000000]
    if not targets:return option(goal='unavailable_'+material)
    target=min(targets,key=lambda e:math.dist(o['own_state']['position_m'],e['position_m']))
    return approach(o,target,option('gather',dict(mass_kg=.05),target['entity_id'],1,'prepare_supplies'))


def choose(o, s, mode='weather'):
    known=memory(o,s); own=o['own_state']; body=own['body']; env=own.get('weather',{})
    if not own['alive']:return None
    severe=env.get('cold_burden',0)>.2 or env.get('wetness',0)>.25 or env.get('felt_temperature_c',20)<5
    if severe:s['exposure_latch']=True
    elif env.get('cold_burden',0)<.12 and env.get('wetness',0)<.12:s['exposure_latch']=False
    # Finish an actual supply trip once started. Routine half-full needs must
    # not repeatedly interrupt a short journey to protection; urgent needs do.
    if s['need'] and body['hunger' if s['need']=='food' else 'thirst']<.5:s['need']=None
    if env.get('shelter_id'):
        if s['sheltered_since'] is None:s['sheltered_since']=int(o['tick'])
    else:s['sheltered_since']=None
    settling=s['sheltered_since'] is not None and (int(o['tick'])-s['sheltered_since'])*o['dt_s']<30
    threshold=.8 if mode=='weather' and s['exposure_latch'] and (not env.get('shelter_id') or settling) else .5 if mode=='survival' else .6
    needs=sorted(('food','water'),key=lambda k:body['hunger' if k=='food' else 'thirst'],reverse=True)
    for k in needs:
        if body['hunger' if k=='food' else 'thirst']>=threshold or s['need']==k:
            s['need']=k
            if s['goal'] in ('build_simple_shelter','repair_shelter','seek_observed_shelter'):s['preemptions']+=1
            return supplies(o,known,k)
    if mode=='survival':return option(goal='rest_survival')
    visible={e['entity_id']:e for e in o['visible_entities']}
    roofs=[e for e in known if e['kind']=='lean_to']
    if s['exposure_latch'] and not env.get('shelter_id') and roofs:
        s['seek_steps']+=1
        if s['seek_steps']>48:
            for e in roofs:s['memory'].pop(e['entity_id'],None)
            s['completed'].append(dict(goal='seek_observed_shelter',outcome='blocked',tick=o['tick'],reason='route_budget'))
            s['seek_steps']=0;s['fallback']+=1
            return option(goal='blocked_shelter_route')
        target=min(roofs,key=lambda e:math.dist(own['position_m'],e['position_m']))
        # Different local slots keep multiple bodies from seeking the same center.
        index=int(o['agent_id'].split('-')[-1])-1
        offsets=[[-.3,-.3],[.3,-.3],[-.3,.3],[.3,.3]]
        q=[target['position_m'][i]+offsets[index%4][i] for i in range(2)]
        return go(o,q,'seek_observed_shelter')
    assigned=s['assigned']
    repairs=[e for e in env.get('observed_shelters',[]) if e['complete'] and e['condition']<(.999 if assigned and assigned['goal']=='repair_shelter' else .9)]
    if repairs:
        target=visible[repairs[0]['entity_id']]
        if int(own['inventory_ug'].get('wood',0))>=100000000:
            return approach(o,target,option('repair_shelter',target=target['entity_id'],duration=3,goal='repair_shelter'))
        piles=[e for e in known if e['kind']=='wood' and int(e['mass_ug'])>=100000000]
        if piles:return approach(o,piles[0],option('collect_wood',dict(material='wood',mass_kg=.1),piles[0]['entity_id'],1,'repair_shelter'))
    if assigned and assigned['goal']=='repair_shelter' and not repairs:
        s['completed'].append(dict(goal='repair_shelter',outcome='unavailable_or_satisfied',tick=o['tick']))
        s['assigned']=None;assigned=None
    if env.get('shelter_id') and not assigned:return option(duration=1,goal='reduce_exposure')
    if body['fatigue']>.75:return option(goal='rest_fatigue')
    if assigned and assigned['goal']=='prepare_supplies':
        for k in ('food','water'):
            if int(own['inventory_ug'].get(k,0))<100000000:
                candidates=[e for e in known if e['kind']==k and int(e['mass_ug'])>=50000000]
                if candidates:return approach(o,candidates[0],option('gather',dict(mass_kg=.05),candidates[0]['entity_id'],1,'prepare_supplies'))
                return option(goal='unavailable_'+k)
        s['completed'].append(dict(goal='prepare_supplies',tick=o['tick'],origin='operator_assigned'));s['assigned']=None;assigned=None
    if (s['exposure_latch'] or assigned) and int(o['tick'])>=s['blocked_until']:
        s['build_steps']+=1
        if s['build_steps']>96 or s['failures']>=6:
            s['completed'].append(dict(goal='build_simple_shelter',outcome='blocked',tick=o['tick'],reason='bounded_retries_or_scarcity'))
            s['assigned']=None;s['blocked_until']=int(o['tick'])+math.ceil(120/o['dt_s']);s['build_steps']=0;s['failures']=0
            return option(goal='blocked_build')
        repair=next((e for e in env.get('observed_shelters',[]) if e['complete'] and e['condition']<.9),None)
        if repair and int(own['inventory_ug'].get('wood',0))>=100000000:
            target=visible.get(repair['entity_id'])
            return approach(o,target,option('repair_shelter',target=repair['entity_id'],duration=3,goal='repair_shelter'))
        site=next((e for e in known if e['kind']=='construction' and e.get('recipe_id')=='lean_to'),None)
        if site:return approach(o,site,option('work_construction',target=site['entity_id'],duration=3,goal='build_simple_shelter'))
        for material, amount in [('wood',800000000),('fiber',100000000)]:
            missing=amount-int(own['inventory_ug'].get(material,0))
            if missing>0:
                piles=[e for e in known if e['kind']==material and int(e['mass_ug'])>=missing]
                if piles:
                    target=min(piles,key=lambda e:math.dist(own['position_m'],e['position_m']))
                    return approach(o,target,option('collect_wood',dict(material=material,mass_kg=missing/1e9),target['entity_id'],1,'build_simple_shelter'))
                trees=[e for e in known if e['kind']=='tree' and int(e.get('biomass_ug',e['mass_ug']))>=1000000000]
                if trees:return approach(o,trees[0],option('harvest_branch',dict(mass_kg=1),trees[0]['entity_id'],1,'build_simple_shelter'))
                s['search']+=1
                if s['search']>24:
                    s['completed'].append(dict(goal='build_simple_shelter',outcome='blocked',tick=o['tick'],reason='local_material_search_budget'))
                    s['assigned']=None;s['blocked_until']=int(o['tick'])+math.ceil(120/o['dt_s']);s['search']=0;s['fallback']+=1
                    return option(goal='blocked_materials')
                # Authored bounded sweep, not remembered hidden resource positions.
                n=s['search']//3; bounds=o['world_bounds_m']
                return go(o,[min(bounds['width']-2,4+8*(n//4)),min(bounds['height']-2,4+8*(n%4))],'search_materials')
        pos=own['position_m']
        candidates=assigned.get('position_m') if assigned else None
        positions=[candidates] if candidates else [[pos[0]+1.4*math.cos(i*math.tau/8),pos[1]+1.4*math.sin(i*math.tau/8)] for i in range(8)]
        for q in positions:
            if not q or not 1.1<=q[0]<=o['world_bounds_m']['width']-1.1 or not 1.1<=q[1]<=o['world_bounds_m']['height']-1.1:continue
            if math.dist(pos,q)>1.5:return go(o,[q[0]-1.4,q[1]],'build_simple_shelter')
            if any(e['radius_m']>0 and math.dist(q,e['position_m'])<1.1+e['radius_m'] for e in o['visible_entities']):continue
            return option('begin_construction',dict(recipe_id='lean_to',x_m=q[0],y_m=q[1]),duration=1,goal='build_simple_shelter')
        s['failures']+=1
        return option(goal='blocked_site')
    return option(goal='reduce_exposure')


def advance(w, policies, agent, mode='weather', assignment=None):
    if mode not in ('weather','survival'):raise ValueError('Unknown weather policy')
    s=policies.setdefault(agent,state())
    if assignment:
        if assignment['goal'] not in ('build_simple_shelter','repair_shelter','prepare_supplies'):raise ValueError('Unknown weather assignment')
        s['assigned']=assignment;s['build_steps']=0;s['failures']=0
    o=w.observe_batch([agent])[0]
    choice=choose(o,s,mode)
    if choice is None:return dict(dead=True,agent=agent)
    choice['origin']='operator_assigned_execution' if s['assigned'] else 'authored_survival_baseline' if mode=='survival' else 'authored_weather_baseline'
    s['serial']+=1;s['decisions']+=1;s['goal']=choice['goal']
    request=dict(schema_version=1,run_id=o['run_id'],request_id=f"weather-{agent}-{s['serial']}",agent_id=agent,
                 observation_version=o['tick'],action_type=choice['action'],target_ids=choice['targets'],parameters=choice['parameters'],requested_duration=choice['duration'])
    result=w.submit(request,agent)
    if result['status']=='accepted':
        w.step(math.ceil(choice['duration']/o['dt_s']))
        result=next(r for r in w.observe_batch([agent])[0]['recent_action_results'] if r['request_id']==request['request_id'])
    if result['status']!='completed':s['failures']+=1
    if choice['goal'].startswith(('blocked_','unavailable_')):s['fallback']+=1
    after=w.observe_batch([agent])[0]
    if choice['action']=='work_construction' and any(e['kind']=='lean_to' and e['entity_id'] in choice['targets'] for e in after['visible_entities']):
        s['completed'].append(dict(goal='build_simple_shelter',outcome='completed',tick=after['tick'],request_id=request['request_id'],origin='operator_assigned' if s['assigned'] else 'authored_autonomous'))
        s['assigned']=None;s['build_steps']=0
    if choice['action']=='repair_shelter' and result['status']=='completed':
        s['completed'].append(dict(goal='repair_shelter',outcome='completed',tick=after['tick'],request_id=request['request_id'],origin='authored_baseline'))
        s['assigned']=None
    s['completed']=s['completed'][-32:]
    s['last']=dict(choice=choice,receipt=result,observed_tick=o['tick'],own_observation_sha256=hashlib.sha256(str(o).encode()).hexdigest())
    return dict(before=o,choice=choice,request=request,receipt=result,after=after)
