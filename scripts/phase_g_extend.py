"""Continue one existing G life under an explicit wall limit; never initialize."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import stabilization as stable,storage  # noqa: E402
from phase_g_demo import collect  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--target-seconds',type=float,default=900);p.add_argument('--wall-seconds',type=float,default=240)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    before=collect(args.db);current=before['snapshot']['simulated_time_s']
    if not current<args.target_seconds<=900 or not 0<args.wall_seconds<=240:p.error('existing-life target must increase time up to900; wall budget up to240')
    started=time.perf_counter();result=stable.run(args.db,args.target_seconds-current,args.wall_seconds)
    after=collect(args.db)
    report={'path':str(args.db.resolve()),'initial_simulated_s':current,'final_simulated_s':after['snapshot']['simulated_time_s'],
            'wall_s':time.perf_counter()-started,'run':result,'before':before,'after':after,
            'replay':storage.replay(args.db),'note':'Continuation of the same saved life; no new goals, knowledge, bodies, resources or models.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('before','after','replay')},indent=2))


if __name__=='__main__':main()
