"""Offline, explicitly opt-in emotion copy attachment and durable execution."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from underworld import emotion_store as store, weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['attach','inspect','step','policy','save','replay'])
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--destination',type=Path)
    p.add_argument('--profile',choices=['learned','frozen','disconnected','disabled'],default='learned')
    p.add_argument('--agent',default='agent-1');p.add_argument('--ticks',type=int,default=20)
    p.add_argument('--id',help='Durable identity; repeat exactly to retry safely')
    a=p.parse_args()
    if a.command in ('attach','save') and not a.destination:p.error('An unused --destination is required')
    if a.command in ('step','policy') and not a.id:p.error('A durable --id is required')
    if a.command=='attach':result=store.attach(a.db,a.destination,[a.agent],a.profile)
    elif a.command=='save':
        store.inspect(a.db);weather.save(a.db,a.destination);result=store.inspect(a.destination)
    elif a.command=='replay':result=store.replay(a.db)
    elif a.command=='step':result=store.commit(a.db,dict(kind='step',ticks=a.ticks),a.id)
    elif a.command=='policy':result=store.commit(a.db,dict(kind='emotion-policy',agent=a.agent),a.id)
    else:result=store.inspect(a.db)
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
