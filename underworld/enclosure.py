"""One bounded authored empty-pen blueprint, never capture or hidden geometry."""
import math


def blueprint(center):
    x,y=center
    points=[('fence',x+dx,y+1.8) for dx in (-1.8,-.6,.6,1.8)]
    points += [('fence',x+dx,y+dy) for dx in (-1.8,1.8) for dy in (-.6,.6)]
    points += [('fence',x+dx,y-1.8) for dx in (-1.8,.6,1.8)]
    points += [('gate',x-.6,y-1.8)]
    return [('storage_box',x,y-3.2),*points]


def structure(e,t,o,recipe,point,slot):
    from . import planning as p
    ids=t.setdefault('enclosure_ids',{})
    visible=o['visible_entities'];own=o['own_state']
    known=ids.get(slot)
    target=next((x for x in visible if x['entity_id']==known),None) if known else next((x for x in visible if x.get('owner_id')==o['agent_id'] and x.get('recipe_id')==recipe and math.dist(x['position_m'],point)<.01 and x['kind'] in ('construction',recipe)),None)
    confirmed=t.setdefault('enclosure_observations',{})
    if not target and slot in confirmed:return [],True,None
    if target:
        ids[slot]=target['entity_id']
        if target['kind']==recipe:
            if recipe=='gate' and target['radius_m']==0:
                operation=p._option('toggle_gate',target=target['entity_id'],source='pen:'+slot)
            else:
                confirmed[slot]={'entity_id':target['entity_id'],'position_m':target['position_m'],'kind':recipe,'tick':o['tick']}
                return [],True,None
        else:operation=p._option('work_construction',target=target['entity_id'],duration=max(1,(8 if recipe=='storage_box' else 4)-target['work_s']),source='pen:'+slot)
        choice=p._approach(o,target,operation)
        return ([choice],False,None) if choice else ([],False,'pen_component_inaccessible')
    if known:
        choice=p._approach(o,{'position_m':point,'radius_m':.5},p._option('inspect',target=known,source='pen:'+slot))
        if choice and choice['action']=='move':return [choice],False,None
        return [],False,'remembered_pen_component_not_observed'
    if any(math.dist(point,x['position_m'])<.5+(x['radius_m'] or .5)-1e-9 for x in visible if x['radius_m']>0 or x['kind']=='gate'):
        return [],False,'observed_pen_site_occupied'
    n=800000000 if recipe=='storage_box' else 400000000
    if int(own['inventory_ug'].get('plank',0))<n:
        options,reason=p._planks(e,t,o);return options,False,reason
    if recipe=='gate':
        # Reserve the final gate from the outside, so closing the barrier cannot
        # strand its builder inside an empty pen without food or water.
        pos=own['position_m']
        if not (pos[1]<=point[1]-.8 and .8<=math.dist(pos,point)<=1.4):
            solids=[x for x in visible if x['radius_m']>0]
            for dx in (-.6,0,.6):
                destination=[point[0]+dx,point[1]-1.1]
                if not p._segment_clear(destination,destination,solids):continue
                step=p._route(o,destination)
                if step and math.dist(pos,step)>.05:
                    return [p._option('move',{'x_m':step[0],'y_m':step[1]},duration=max(o['dt_s'],math.ceil(math.dist(pos,step)/o['dt_s'])*o['dt_s']),source='pen_gate_outside_approach')],False,None
            return [],False,'outside_gate_stance_inaccessible'
    choice,ready=p.placement_stance(o,point,'pen_site_approach:'+slot)
    if not ready:return ([choice],False,None) if choice else ([],False,'pen_site_inaccessible')
    return [p._option('begin_construction',{'recipe_id':recipe,'x_m':point[0],'y_m':point[1]},source='pen:'+slot)],False,None


def choices(e,t,o):
    center=t['params'].get('position_m')
    if center is None:return [],False,'pen_center_required'
    points=blueprint(center);bounds=o['world_bounds_m']
    if any(not .5<=x<=bounds['width']-.5 or not .5<=y<=bounds['height']-.5 for _,x,y in points):
        return [],False,'pen_blueprint_out_of_bounds'
    for i,(recipe,x,y) in enumerate(points):
        options,done,reason=structure(e,t,o,recipe,[x,y],str(i))
        if not done:return options,False,reason
    return [],True,None


def store_offcuts(e,t,o,missing):
    """Free actual carrying space in an observed/own-remembered storage box."""
    from . import planning as p
    own=o['own_state'];waste=int(own['inventory_ug'].get('wood_offcut',0))
    if not waste:return [],'carrying_capacity_requires_explicit_storage'
    boxes=[x for x in o['visible_entities'] if x['kind']=='storage_box' and x.get('owner_id')==o['agent_id']]
    for box in boxes:
        room=4000000000-sum(int(v) for v in box.get('inventory_ug',{}).values())
        n=min(waste,room,max(1,missing))
        if n<=0:continue
        c=p._approach(o,box,p._option('store_item',{'material':'wood_offcut','mass_kg':n/1e9},box['entity_id'],source='offcut_storage:'+box['entity_id']))
        if c:return [c],None
    if t.get('enclosure_ids',{}).get('0'):
        point=blueprint(t['params']['position_m'])[0][1:]
        c=p._approach(o,{'position_m':point,'radius_m':.5},p._option('inspect',target=t['enclosure_ids']['0']))
        if c and c['action']=='move':return [c],None
    return [],'no_observed_storage_capacity'
