"""One explicit CLI for persistent developmental research; never resets an existing save."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import developmental as dev, symbols  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('init','symbol-init','status','food-trial','demonstrate','reference','reconcile','archive'))
    p.add_argument('--db',type=Path,required=True);p.add_argument('--seed',type=int,default=41)
    p.add_argument('--agent',default='agent-1');p.add_argument('--listener',default='agent-2')
    p.add_argument('--target');p.add_argument('--alternatives',nargs='*',default=[])
    args=p.parse_args()
    try:
        if args.command=='init':result=dev.initialize(args.db,seed=args.seed)
        elif args.command=='symbol-init':result=symbols.initialize(args.db,args.seed)
        elif args.command=='status':result=dev.audit(args.db)
        elif args.command=='archive':result=dev.archive(args.db)
        elif args.command=='reconcile':result=dev.reconcile(args.db,args.agent)
        else:
            if dev.audit(args.db)['pending']:raise ValueError('reconcile pending experience before a new task')
            if not args.alternatives:p.error('task requires explicit --alternatives')
            if args.command=='food-trial':
                choice=dev.choose(args.db,args.agent,args.alternatives)
                experience=(dev.execute(args.db,args.agent,'gather',[choice['target']],{'mass_kg':.001},
                    learn_food=True,prediction=choice) if choice['target'] else
                    dev.execute(args.db,args.agent,'rest',prediction=choice,update_memory=False))
                result={'mode':'online_native_food_trial','decision':choice,'experience':experience,
                        'origin':'assigned bounded task; learned source choice'}
            else:
                if not args.target:p.error('speaker requires a private --target assignment')
                if args.target not in args.alternatives:p.error('private target must belong to the offered set')
                if args.command=='demonstrate':
                    token=symbols.coin(args.db,args.agent,args.target)
                    symbols.begin_attention(args.db,args.listener,args.alternatives)
                    deposited=dev.execute(args.db,args.agent,'deposit',[args.target],{'mass_kg':.001})
                    spoken=dev.execute(args.db,args.agent,'speak',parameters={'text':token})
                    feedback=symbols.learn_attention(args.db,args.listener,args.agent)
                    result={'origin':'authored native deposit teaching scaffold','deposit':deposited,
                            'speech':spoken,'feedback':feedback}
                else:
                    before=dev.own_observation(args.db,args.listener)
                    seq=max((int(r['source_event_seq']) for r in before['audible_reports']),default=0)
                    token=symbols.production_token(args.db,args.agent,args.target)
                    spoken=dev.execute(args.db,args.agent,'speak',parameters={'text':token})
                    decision=symbols.select_reference(args.db,args.listener,args.agent,args.alternatives,seq)
                    inspected=dev.execute(args.db,args.listener,'inspect',[decision['target']],update_memory=False)
                    actual=inspected['receipt']['observable_effects'].get('description','').split(':')[0]
                    result={'speech':spoken,'decision':decision,'inspection':inspected,
                            'operator_scored_correct':inspected['receipt']['status']=='completed' and actual==args.target,'vocabulary_updates':0,
                            'origin':'assigned message-only reference; target absent from listener inputs'}
        print(json.dumps(result,indent=2))
        return 0
    except (ValueError,RuntimeError,OSError,sqlite3.Error) as error:
        p.exit(2,f'developmental: {error}\n')


if __name__=='__main__':raise SystemExit(main())
