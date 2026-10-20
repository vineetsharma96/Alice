"""Run a new, explicitly operator-assigned one-person production experiment."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage, stabilization
from underworld.config import load
from underworld.lease import Lease
from underworld.workshop import AssignedProcedure
from underworld.wire import dumps


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='NEW directory, never overwrites an experiment')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    path=args.output/'run.sqlite';backup=args.output/'mid-construction.sqlite'
    start=time.perf_counter();config=load(ROOT/'config/living-world.toml')
    config['world'].update(population=1,width_m=8.,height_m=8.)
    config['agency']['tree_growth_kg_s']=0
    storage.create(path,config,scripted=False);stabilization.attach(path,model=False,call_limit=0)
    assignment=dict(version='woodcraft-demo/1',agent='agent-1',source='operator_assigned_procedure',
                    task='bootstrap axe, fell tree, cut planks, build box and store offcuts',
                    learned=False,model_calls=0,executor='authored_fixture_route',
                    source_sha256=hashlib.sha256((ROOT/'underworld/workshop.py').read_bytes()).hexdigest())
    # Knowledge/procedure assignment is separate from native truth and earned skill.
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('CREATE TABLE assigned_procedures(agent TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL)')
        payload=dumps(assignment);db.execute('INSERT INTO assigned_procedures VALUES(?,?,?)',('agent-1',payload,storage.digest(payload)))
    h=AssignedProcedure(db=path);initial=h.snapshot()
    with Lease(path):
        site=h.site();h.submit('work_construction',[site],duration=8);h.step(10)
        storage.save(path,'mid-construction',backup)
        partial=h.snapshot();h.step(35)
    # Resume the backup in a new interpreter. No resource/body/identity reset.
    child_start=time.perf_counter()
    child=subprocess.run([sys.executable,'-m','underworld','advance','--db',str(backup),'--ticks','35'],cwd=ROOT,env=os.environ.copy(),capture_output=True,text=True,timeout=90)
    child_elapsed=time.perf_counter()-child_start
    if child.returncode:raise RuntimeError(child.stderr)
    parity=storage.inspect(path)['state_hash']==storage.inspect(backup)['state_hash']
    with Lease(path):
        h.act('store_item',[site],{'material':'wood_offcut','mass_kg':.2})
        # Operator evidence only. Contents are not supplied to target selection.
        stored=next(e for e in h.snapshot()['entities'] if e['entity_id']==site)['inventory_ug']
        h.act('take_item',[site],{'material':'wood_offcut','mass_kg':.2})
    final=h.snapshot();replay=storage.replay(path)
    result=dict(assignment=assignment,config=config,db=str(path.resolve()),initial=initial,partial=partial,final=final,
                receipts=h.receipts,stored_contents_ug=stored,fresh_process_resume_matches=parity,
                child_returncode=child.returncode,child_wall_s=child_elapsed,
                simulated_s=final['simulated_time_s']-initial['simulated_time_s'],wall_s=time.perf_counter()-start,
                replay=replay,learned_planning=False,model_calls=0)
    with closing(storage._connect(path,readonly=True)) as db:
        result['native_events']=[json.loads(row[0]) for row in db.execute('SELECT payload FROM events ORDER BY seq')]
    (args.output/'evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if not parity or not replay['replay_matches']:raise AssertionError('continuity mismatch')
    print(json.dumps(dict(evidence=str((args.output/'evidence.json').resolve()),simulated_s=result['simulated_s'],wall_s=result['wall_s'],fresh_process_resume_matches=parity,replay=replay),indent=2))


if __name__=='__main__':main()
