"""Measured native broken-tool recovery; fixture aging is explicitly declared."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shlex
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from underworld import storage,stabilization as stable,planning
from underworld.config import load
from underworld.native import load_native
from underworld.workshop import AssignedProcedure
from ecology_fixtures import render,balances


def prepare(path,seed,utility):
    cfg=load(ROOT/'config/living-world-e.toml');cfg['seed']=seed
    cfg['world'].update(population=1,width_m=8,height_m=8,dt_s=.2);cfg['ecology']['enabled']=False
    cfg['agency']['policy']='utility' if utility else 'none';storage.create(path,cfg,scripted=utility)
    with closing(storage._connect(path,readonly=True)) as db:w,_,_,_=storage._head(db)
    h=AssignedProcedure(world=w);tool=h.plank_stock()
    lines=h.world.checkpoint().splitlines();n=int(lines[3])
    for i in range(4,4+n):
        row=shlex.split(lines[i])
        if row[0]==tool:row[20+2*int(row[6])]='1';lines[i]=render(row)
    w=load_native().World.restore('\n'.join(lines)+'\n',h.world.snapshot()['run_id']);h.world=w
    h.act('begin_construction',params={'recipe_id':'storage_box','x_m':6.7,'y_m':4.3})
    box=h.entity('construction')['entity_id'];h.act('work_construction',[box],duration=8)
    h.act('store_item',[box],{'material':'wood_offcut','mass_kg':.2})
    wood=next(x for x in h.observe()['visible_entities'] if x['kind']=='wood' and int(x['mass_ug'])>=1000000000)
    h.act('collect_wood',[wood['entity_id']],{'material':'wood','mass_kg':1})
    h.act('craft',params={'recipe_id':'planks','tool_id':tool},duration=3)
    assert not h.observe()['own_state']['tools'];w.check_invariants()
    state=w.checkpoint();tick=int(w.snapshot()['tick']);hashed=storage.digest(state)
    with closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');db.execute('UPDATE run SET state=?,state_hash=?',(state,hashed))
        db.execute("UPDATE checkpoints SET tick=?,state=?,state_hash=? WHERE name='initial'",(tick,state,hashed));db.commit()
    return dict(preparation_simulated_s=w.snapshot()['simulated_time_s'],receipts=h.receipts,initial_native=state,initial_tick=tick)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    r=dict(protocol_sha256=hashlib.sha256((ROOT/'docs/PHASE_E_TOOL_RECOVERY_SUPPLEMENT.md').read_bytes()).hexdigest(),
           controller_source_id=stable.source_id(),development_seeds=[21],confirmation_seeds=[2129,2149],runs=[])
    for seed in (21,2129,2149):
        for arm in ('utility','authored','episodic_only','adaptive','model_assisted'):
            folder=args.output/f'{seed}-{arm}';folder.mkdir();path=folder/'run.sqlite'
            start=time.perf_counter();prep=prepare(path,seed,arm=='utility');prep_wall=time.perf_counter()-start
            (folder/'preparation.json').write_text(json.dumps(prep,indent=2)+'\n')
            start=time.perf_counter();history=None
            if arm=='utility':storage.advance(path,300)
            else:
                stable.attach(path,['agent-1'],call_limit=0);planning.assign(path,'agent-1','craft_tool',mode=arm)
                for _ in range(300):
                    stable.step(path);s=stable.status(path)
                    if not s['tasks']['active']:history=s['tasks']['history'][-1];break
                    if time.perf_counter()-start>180:break
            own=storage.observe(path,['agent-1'])[0]['own_state'];final=storage.inspect(path)
            with closing(storage._connect(path,readonly=True)) as db:
                w,_,_,_=storage._head(db);balance=balances(w)
            row=dict(seed=seed,arm=arm,preparation_wall_s=prep_wall,preparation_simulated_s=prep['preparation_simulated_s'],
                     wall_s=time.perf_counter()-start,simulated_s=(int(final['tick'])-prep['initial_tick'])*final['dt_s'],
                     history=history,new_usable_tool=bool(own['tools']),alive=own['alive'],balances=balance,
                     model_calls=0 if arm=='utility' else stable.status(path)['tasks']['calls'],replay=storage.replay(path))
            r['runs'].append(row);args.evidence.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(row),flush=True)
    r['passed']=all(not any(x['balances'].values()) and x['replay']['replay_matches'] and (x['arm']=='utility' or (x['new_usable_tool'] and x['history']['executor_goal_credit'])) for x in r['runs'])
    args.evidence.write_text(json.dumps(r,indent=2)+'\n');return 0 if r['passed'] else 1


if __name__=='__main__':sys.exit(main())
