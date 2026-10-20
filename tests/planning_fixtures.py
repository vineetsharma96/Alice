"""Declared NEW-world E layouts; no live agent receives these diagnostics."""
from contextlib import closing
from pathlib import Path

from underworld import storage,stabilization
from underworld.config import load
from ecology_fixtures import layout,caretaker_layout

ROOT=Path(__file__).resolve().parents[1]


def create(path,seed=21,ecology=False,positions=None,structures=(),care=False,managed=True,utility=False,scarce=False,neutral_warmup_ticks=0):
    config=load(ROOT/'config/living-world-e.toml');config['seed']=seed
    config['world'].update(population=1,width_m=24 if care else 8,height_m=24 if care else 8)
    config['ecology']['enabled']=ecology or care
    if care:
        config['world']['dt_s']=.2;config['ecology']['forage_kg']=0
        config['agency'].update(food_kg=16,water_kg=8)
    if scarce:config['agency']['food_kg']=0;config['ecology']['forage_kg']=0
    if utility:config['agency']['policy']='utility'
    storage.create(path,config,scripted=utility)
    if positions or structures or care or neutral_warmup_ticks:
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');w,_,_,_=storage._head(db)
            # caretaker_layout starts a separate declared native fixture. Restore
            # its physical state with this new run ID before publishing tick 0.
            if care:
                from underworld.native import load_native
                w=load_native().World.restore(caretaker_layout(seed).checkpoint(),w.snapshot()['run_id'])
            else:w=layout(w,positions=positions,structures=structures)
            if neutral_warmup_ticks:w.step(neutral_warmup_ticks)
            state=w.checkpoint();hashed=storage.digest(state)
            db.execute('UPDATE run SET state=?,state_hash=?',(state,hashed))
            db.execute("UPDATE checkpoints SET tick=?,state=?,state_hash=? WHERE name='initial'",(int(w.snapshot()['tick']),state,hashed));db.commit()
    if managed:stabilization.attach(path,['agent-1'],call_limit=0)
    return path


def until_done(path,ticks=800,provider=None):
    for _ in range(ticks):
        stabilization.step(path,provider=provider)
        state=stabilization.status(path)
        if not state['tasks']['active']:return state['tasks']['history'][-1]
    raise AssertionError('task did not finish within test tick bound: '+str(state))


def collision_layout(path,seed=21):
    """Finite wood piles funded from initial tree biomass, before tick zero."""
    import shlex
    from ecology_fixtures import render
    from underworld.native import load_native
    config=load(ROOT/'config/living-world-e.toml');config['seed']=seed
    config['world'].update(population=2,width_m=8,height_m=8,dt_s=.2)
    config['ecology']['enabled']=False
    storage.create(path,config,scripted=False)
    with closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');w,_,_,_=storage._head(db)
        lines=w.checkpoint().splitlines();n=int(lines[3]);rows=[shlex.split(x) for x in lines[4:4+n]]
        source=next(x for x in rows if x[0]=='resource-4')
        for name,position in (('wood-a',(5,3)),('wood-b',(2,6))):
            row=list(source);row[0]=name;row[1]='wood';row[2:4]=list(map(str,position));row[5]='500000000';rows.append(row)
        for row in rows:
            if row[0]=='agent-1':row[2:4]=['2','3']
            if row[0]=='agent-2':row[2:4]=['4','2']
            if row[0]=='tree-1':
                row[2:4]=['1','6'];row[5]=str(int(row[5])-1000000000);row[16]=row[5]
            if row[0]=='terrain-1':row[2:4]=['4','6']
        lines[3]=str(len(rows));lines[4:4+n]=list(map(render,rows))
        w=load_native().World.restore('\n'.join(lines)+'\n');w.check_invariants()
        state=w.checkpoint();hashed=storage.digest(state)
        db.execute('UPDATE run SET state=?,state_hash=?',(state,hashed));db.execute("UPDATE checkpoints SET state=?,state_hash=? WHERE name='initial'",(state,hashed));db.commit()
    stabilization.attach(path,['agent-1'],call_limit=0)
    return path
