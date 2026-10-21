"""Opt-in gap profile CLI. Never changes old H0-H5 source contracts or resets saves."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import adaptive as ad,context_teaching as ct  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['init','attach','status','step','cohort-step','observe','share','encode','attention','learn-location','act','teaching-attach','attend','teach'])
    p.add_argument('--db',type=Path,required=True);p.add_argument('--seed',type=int,default=53)
    p.add_argument('--agent',default='agent-1');p.add_argument('--agents',nargs='+')
    p.add_argument('--listener',default='agent-2');p.add_argument('--target');p.add_argument('--candidates',nargs='*',default=[])
    p.add_argument('--id');p.add_argument('--text');p.add_argument('--mass',type=float,default=.001)
    p.add_argument('--action',choices=['rest','gather','deposit','speak','eat','drink','inspect'])
    p.add_argument('--duration',type=float,default=1);p.add_argument('--coin',action='store_true')
    p.add_argument('--site',action='store_true');p.add_argument('--mode',choices=['learned','whole','muted'],default='learned')
    args=p.parse_args()
    try:
        if args.command=='init':r=ad.initialize(args.db,args.seed)
        elif args.command=='attach':
            if not args.agents:p.error('attach requires explicit --agents; use a working copy, never scored evidence')
            r=ad.attach(args.db,args.agents)
        elif args.command=='status':r=ad.audit(args.db)
        elif args.command=='teaching-attach':
            if not args.agents:p.error('teaching-attach requires --agents')
            ct.attach(args.db,args.agents);r=ct.audit(args.db)
        elif args.command=='attend':r=ct.observe(args.db,args.agent)
        elif args.command=='teach':r=ct.teacher_step(args.db,args.agent)
        elif args.command=='step':r=ad.step(args.db,args.agent,args.mode,cycle_id=args.id)
        elif args.command=='cohort-step':r=ad.cohort_step(args.db)
        elif args.command=='observe':r={'cell':ad.refresh(args.db,args.agent,args.site)}
        elif args.command=='share':r=ad.share_step(args.db,args.agent)
        elif args.command=='encode':
            if not args.target:p.error('encode requires --target')
            r={'signal':ad.encode_location(args.db,args.agent,args.target,args.coin)}
        elif args.command=='attention':
            if not args.id:p.error('attention requires --id')
            r=ad.begin_location(args.db,args.listener,args.id,args.candidates)
        elif args.command=='learn-location':
            if not args.id:p.error('learn-location requires --id')
            r=ad.learn_location(args.db,args.listener,args.agent,args.id)
        else:
            if not args.id or not args.action:p.error('act requires --id and --action')
            parameters=({'text':args.text} if args.action=='speak' else {'mass_kg':args.mass} if args.action in ('gather','deposit','eat','drink') else {})
            r=ad.perform(args.db,args.agent,args.id,args.action,[args.target] if args.target else [],parameters,args.duration)
        print(json.dumps(r,indent=2));return 0
    except (ValueError,RuntimeError,OSError,sqlite3.Error) as error:p.exit(2,f'adaptive: {error}\n')


if __name__=='__main__':raise SystemExit(main())
