"""One four-person world: real in-flight backup and restart across rotation."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage,stabilization as stable,planning,runtime,memory  # noqa: E402
from phase_g_demo import initialize  # noqa: E402


def state(path):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');world,_,meta,head=storage._head(db);world.check_invariants()
        tables={t:db.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in
                ('identities','episodes','relationships','plans','social_observations',
                 'stabilization_meta','stabilization_agents','stabilization_events')}
        ctl=runtime.verify_control(db);ctl.pop('chain_head',None)
        epochs=[]
        for payload, in db.execute('SELECT payload FROM runtime_epochs ORDER BY epoch'):
            r=json.loads(payload)
            epochs.append({k:v for k,v in r.items() if k not in ('archive_sha256','chain_hash','previous_chain')})
        return {'head':head,'tick':world.snapshot()['tick'],'cognitive':memory.checksum(db),
                'tables':tables,'runtime_semantics':ctl,'epoch_semantics':epochs,
                'replay_after_id':meta['replay_after_id'],'retained_replay_start_tick':meta['retained_replay_start_tick']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    args.directory.mkdir(parents=True,exist_ok=False)
    primary=args.directory/'world.sqlite';backup=args.directory/'resumed.sqlite'
    _,lesson,_=initialize(primary,21)
    planning.assign(primary,'agent-1','craft_tool')
    planning.assign(primary,'agent-2','feed_animal',{'target':'animal-1','lesson_episode_id':lesson})
    stable.run(primary,.5,30)
    assert stable.status(primary)['pending'],'declared backup must be in flight'
    storage.save(primary,'G-inflight',backup)
    started=time.perf_counter();stages=[]
    for duration in (59.5,60):stages.append(stable.run(primary,duration,240))
    primary_wall=time.perf_counter()-started
    assert all(r['status']=='target_reached' for r in stages),stages
    started=time.perf_counter()
    child=subprocess.run([sys.executable,'-m','underworld','living-world','run','--db',str(backup),
                          '--seconds','119.5','--wall-seconds','240'],cwd=ROOT,capture_output=True,text=True,timeout=270)
    child_wall=time.perf_counter()-started
    assert child.returncode==0,child.stderr
    a,b=state(primary),state(backup);equal={k:a[k]==b[k] for k in a}
    assert all(equal.values()),equal
    replay={str(path):storage.replay(path) for path in (primary,backup)}
    archives={str(path):runtime.verify_archives(path) for path in (primary,backup)}
    report={'passed':True,'primary_simulated_s':120,'primary_wall_s':primary_wall,'child_wall_s':child_wall,
            'stages':stages,'child_result':json.loads(child.stdout),'equality':equal,'replay':replay,'archives':archives,
            'note':'Same life; backup at0.5s, native+identity+memory+controller exact across100s rotation. Archive file SHA/derived chain excluded from cross-file equality, individually verified.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
