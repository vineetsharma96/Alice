"""Create a NEW journaled, operator-scaffolded weather viewer demonstration."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import weather_store as store  # noqa: E402
from underworld.weather_tools import JournalWorld, roof, walk  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Do not overwrite demonstration evidence')
    start=time.perf_counter();store.initialize(args.db,population=4,guided=True,food_kg=8,water_kg=16)
    w=JournalWorld(args.db)
    for i in range(2,5):walk(w,[8,3+i],f'agent-{i}')
    target,trace=roof(w)
    for i,q in enumerate(([3.7,3.7],[4.3,3.7],[3.7,4.3],[4.3,4.3]),1):walk(w,q,f'agent-{i}')
    payload=dict(id='viewer-rain',observation_version=w.snapshot()['tick'],duration_s=600,temperature_c=-8,
                 rain_mm_h=12,cloud_fraction=.9,wind_x_m_s=4,wind_y_m_s=1)
    store.commit(args.db,dict(kind='force',parameters=payload));w.step(40)
    result=dict(attribution='operator assigned native setup; forced weather is an external intervention',
                target=target,setup_receipts=trace,final=store.inspect(args.db),replay=store.replay(args.db),wall_s=time.perf_counter()-start)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(replay=result['replay'],wall_s=result['wall_s'])))


if __name__=='__main__':main()
