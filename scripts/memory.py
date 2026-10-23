"""F5 opt-in copy, native actions, save/resume and replay."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from underworld import memory_store as store,weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['attach','inspect','step','policy','save','replay'])
    p.add_argument('--db',type=Path,required=True);p.add_argument('--destination',type=Path)
    p.add_argument('--memory-mode',choices=['connected','disconnected','frozen'],default='connected')
    p.add_argument('--agents',nargs='+');p.add_argument('--agent',default='agent-1')
    p.add_argument('--ticks',type=int,default=40);p.add_argument('--id');a=p.parse_args()
    if a.command in ('attach','save') and not a.destination:p.error('--destination required')
    if a.command in ('step','policy') and not a.id:p.error('--id required')
    if a.command=='attach':r=store.attach(a.db,a.destination,a.agents,memory_mode=a.memory_mode)
    elif a.command=='save':store.inspect(a.db);weather.save(a.db,a.destination);r=store.inspect(a.destination)
    elif a.command=='step':r=store.commit(a.db,dict(kind='step',ticks=a.ticks),a.id)
    elif a.command=='policy':r=store.commit(a.db,dict(kind='emotion-policy',agent=a.agent),a.id)
    elif a.command=='replay':r=store.replay(a.db)
    else:r=store.inspect(a.db)
    print(json.dumps(r,indent=2,allow_nan=False))


if __name__=='__main__':main()
