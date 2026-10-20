"""Declared native test layouts; never used as an inhabitant policy.

Checkpoint editing is confined to NEW test fixtures. Structure composition is
debited from existing tree stock, never silently granted in a running world.
"""
import json
import shlex
from underworld.native import load_native
from underworld.workshop import AssignedProcedure


def render(tokens):
    def token(s):
        try:
            float(s)
            return s
        except ValueError:
            return json.dumps(s)
    return ' '.join(map(token, tokens))


def layout(world, positions=None, fatigue=None, structures=()):
    lines=world.checkpoint().splitlines();count=int(lines[3]);rows=[shlex.split(line) for line in lines[4:4+count]]
    cost=0
    for row in rows:
        if positions and row[0] in positions:row[2:4]=list(map(str,positions[row[0]]))
        if fatigue is not None and row[1]=='animal':row[7+2*int(row[6])+2]=str(fatigue)
    for index,(kind,x,y) in enumerate(structures):
        cost+=800000000 if kind in ('storage_box','trough') else 400000000
        mass=800000000 if kind in ('storage_box','trough') else 400000000
        rows.append(shlex.split(f'"fixture-{index}" "{kind}" {x} {y} .5 {mass} 0 .35 .4 .2 1 1 0 0 "none" 1 0 "{kind}" "agent-1" {8 if mass==800000000 else 4} 0 0 1 "plank" {mass}'))
    for row in rows:
        if row[0]=='tree-2':
            row[5]=str(int(row[5])-cost);row[16]=row[5]
    lines[3]=str(len(rows));lines[4:4+count]=list(map(render,rows))
    return load_native().World.restore('\n'.join(lines)+'\n')


def world(seed=21, forage=2, water=8, rate=0, width=24,population=1):
    w=load_native().World(seed=seed,population=population,width=width,height=width,dt=.2,scripted=False,bodies=True,water_kg=water)
    w.configure_ecology(forage,rate)
    return w


def pen(seed=21, supplied=False):
    w=world(seed,forage=2 if supplied else 0,water=8)
    points=[('gate' if x==6.2 else 'fence',x,5) for x in (5,6.2,7.4,8.6)]
    points += [('fence',x,8.6) for x in (5,6.2,7.4,8.6)]
    points += [('fence',x,y) for x in (5,8.6) for y in (6.2,7.4)]
    positions={'agent-1':(6.2,4),'animal-1':(6.2,6.8),'animal-2':(7.4,7.3),'forage-1':(6.2,6.8),'resource-2':(6.2,6.8 if supplied else 3.2)}
    return layout(w,positions=positions,structures=points)


def harness(w):return AssignedProcedure(world=w)


def caretaker_layout(seed=21):
    """Matched starting inventory; treatment changes only actual care actions.

    Held-out variants translate the pen and alter outside stock. Neither variant
    grants animals hidden resource locations or any new navigation capability.
    """
    base=pen(seed,False)
    # Reuse the native pen, adding an explicitly composed trough.
    w=layout(base,positions={'agent-1':(6.5,7.1),'animal-1':(7.4,6.2),'animal-2':(7.4,7.4),
                            'resource-1':(20,3),'resource-2':(20,4)},structures=[])
    lines=w.checkpoint().splitlines();n=int(lines[3]);rows=[shlex.split(x) for x in lines[4:4+n]]
    # Unique ID because the existing fence IDs already use fixture-N.
    row=shlex.split('"care-trough" "trough" 6.2 6.2 .5 800000000 0 .35 .4 .2 1 1 0 0 "none" 1 0 "trough" "agent-1" 8 0 0 1 "plank" 800000000')
    rows.append(row)
    for r in rows:
        if r[0]=='tree-2':r[5]=str(int(r[5])-800000000);r[16]=r[5]
        if r[0]=='agent-1':r[6]='2';r[7:7]=['food','1000000000','water','1000000000']
        if r[0] in ('resource-1','resource-2'):r[5]=str(int(r[5])-1000000000)
        if seed==101:
            if r[0]=='agent-1':r[2:4]=['7.4','7.4']
            if r[0]=='animal-1':r[2:4]=['6.2','7.4']
            if r[0]=='animal-2':r[2:4]=['7.4','6.2']
            if r[0]=='resource-4':r[2:4]=['7.9','6.8']
        if seed==202:
            if r[0]=='agent-1':r[2:4]=['6.2','6.2']
            if r[0]=='care-trough':r[2:4]=['7.4','6.2']
            if r[0]=='animal-1':r[2:4]=['6.2','7.4']
            if r[0]=='animal-2':r[2:4]=['7.4','7.4']
            if r[0]=='resource-4':r[2:4]=['6.8','7.9']
        if seed==303:
            if r[0]=='agent-1':r[2:4]=['6.2','7.4']
            if r[0]=='animal-1':r[2:4]=['7.4','7.4']
            if r[0]=='animal-2':r[2:4]=['7.4','6.2']
            if r[0]=='resource-4':r[2:4]=['6.8','6.8']
        if seed==404:
            if r[0]=='agent-1':r[2:4]=['7.4','6.2']
            if r[0]=='care-trough':r[2:4]=['7.4','7.4']
            if r[0]=='animal-1':r[2:4]=['6.2','6.2']
            if r[0]=='animal-2':r[2:4]=['6.2','7.4']
            if r[0]=='resource-4':r[2:4]=['6.8','6.8']
        # Held-out geometry differs from the development fixture.
        if r[0].startswith(('animal-','fixture-','care-')) or r[0] in ('agent-1','forage-1') or (seed in (101,202,303,404) and r[0]=='resource-4'):
            dx,dy={21:(0,0),44:(1.1,.6),73:(-.8,1.2),101:(1.1,.6),202:(-.8,1.2),303:(.4,.7),404:(1.0,.3)}.get(seed,(0,0))
            r[2]=str(float(r[2])+dx);r[3]=str(float(r[3])+dy)
    lines[3]=str(len(rows));lines[4:4+n]=list(map(render,rows))
    return load_native().World.restore('\n'.join(lines)+'\n')


def balances(w):
    w.check_invariants();s=w.snapshot();m={k:int(v) for k,v in s['material_totals_ug'].items()};e=s['ecology']
    food=sum(m.get(k,0) for k in ('food','forage','plant_food','eggs'))+int(e['food_residue_ug'])+sum(int(a['food_reserve_ug']) for a in e['animals'].values())
    water=m.get('water',0)+int(e['water_waste_ug'])+sum(int(a['water_reserve_ug']) for a in e['animals'].values())
    return {'food_error_ug':food-s['initial_mass_ug']['food']-s['boundary_sources_ug']['food'],
            'water_error_ug':water-s['initial_mass_ug']['water']-s['boundary_sources_ug']['water'],
            'body_error_ug':m.get('animal',0)-int(e['structural_body_initial_ug'])}
