"""Bounded model-off continuity check; fresh world and fresh-process counterpart."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage,stabilization
from underworld.config import load


def main(config_name="living-world-d.toml",note="One continuous four-inhabitant/two-animal world. Finite food/water; no resets. Tree growth has an explicit biomass boundary source."):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    path=args.output/'run.sqlite';backup=args.output/'resumed.sqlite'
    cfg=load(ROOT/'config'/config_name)
    storage.create(path,cfg,scripted=False);stabilization.attach(path,call_limit=0)
    report=dict(config=cfg,stages=[],model_calls=0,db=str(path.resolve()),backup=str(backup.resolve()),
                note=note)
    def retain():
        args.evidence.parent.mkdir(parents=True,exist_ok=True)
        args.evidence.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    start=time.perf_counter()
    for seconds in (2,8,20,90):
        result=stabilization.run(path,seconds,180);report['stages'].append(result);retain()
        print(json.dumps(result),flush=True)
        if result['status']!='target_reached':return 1
        if seconds==20:storage.save(path,'at-30-seconds',backup)
    report['primary_wall_s']=time.perf_counter()-start;report['final']=storage.inspect(path)
    child_start=time.perf_counter()
    child=subprocess.run([sys.executable,'-m','underworld','living-world','run','--db',str(backup),'--seconds','90','--wall-seconds','180'],cwd=ROOT,capture_output=True,text=True,timeout=210)
    report['child_returncode']=child.returncode;report['child_wall_s']=time.perf_counter()-child_start
    if child.returncode:
        report['child_error']=child.stderr;retain();return 1
    report['child_result']=json.loads(child.stdout)
    report['native_resume_matches']=storage.inspect(backup)['state_hash']==report['final']['state_hash']
    tables={}
    for table in ('identities','episodes','relationships','plans','social_observations','stabilization_meta','stabilization_agents','stabilization_events'):
        with closing(storage._connect(path,readonly=True)) as a,closing(storage._connect(backup,readonly=True)) as b:
            tables[table]=a.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()==b.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
    report['memory_and_scheduler_tables_match']=tables
    with closing(storage._connect(path,readonly=True)) as db:
        report['agents']=[json.loads(p) for p, in db.execute('SELECT payload FROM stabilization_agents ORDER BY agent')]
        report['outcomes']=[json.loads(p) for p, in db.execute('SELECT payload FROM stabilization_events ORDER BY id')]
        report['decisions']=[dict(request=json.loads(q),result=json.loads(r)) for q,r in db.execute('SELECT request,result FROM decisions ORDER BY id')]
    report['passed']=report['native_resume_matches'] and all(tables.values())
    retain();print(json.dumps({k:report[k] for k in ('primary_wall_s','native_resume_matches','memory_and_scheduler_tables_match','passed')}),flush=True)
    return 0 if report['passed'] else 1


if __name__=='__main__':sys.exit(main())
