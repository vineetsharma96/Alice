"""One explicit CLI for persistent developmental research; never resets an existing save."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import developmental as dev, symbols, community, wayfinding as wf, composition as comp  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('init','symbol-init','community-init','community-status','recruit',
        'sequence-init','sequence-status','sequence-encode','sequence-send','sequence-begin','sequence-learn','sequence-reference',
        'wayfinding-init','wayfinding-status','need-step','wayfinding-reconcile',
        'location-remember','location-coin','location-learn','location-receive','scout-observe','scout-send','follow-report',
        'community-demonstrate','community-reference','community-reconcile',
        'status','food-trial','demonstrate','reference','reconcile','archive'))
    p.add_argument('--db',type=Path,required=True);p.add_argument('--seed',type=int,default=41)
    p.add_argument('--agent',default='agent-1');p.add_argument('--listener',default='agent-2')
    p.add_argument('--target');p.add_argument('--alternatives',nargs='*',default=[])
    p.add_argument('--after-seq',type=int,default=0)
    p.add_argument('--communication',choices=('enabled','muted','scrambled','identity'),default='enabled')
    p.add_argument('--frozen',action='store_true')
    p.add_argument('--message-id');p.add_argument('--attention-id');p.add_argument('--text')
    p.add_argument('--sequence-mode',choices=('learned','whole','muted'),default='learned')
    p.add_argument('--coin',action='store_true',help='allow private factor coinage for sequence-encode')
    args=p.parse_args()
    try:
        if args.command=='init':result=dev.initialize(args.db,seed=args.seed)
        elif args.command=='sequence-init':result=comp.initialize(args.db,args.seed)
        elif args.command=='sequence-status':result=comp.audit(args.db)
        elif args.command=='sequence-encode':
            if not args.target:p.error('sequence-encode requires --target')
            result={'signal':comp.encode(args.db,args.agent,args.target,learn=args.coin),
                    'origin':'authored factor encoder with private coined IDs'}
        elif args.command=='sequence-send':
            if not args.message_id or not args.text:p.error('sequence-send requires --message-id and --text')
            result=comp.send(args.db,args.agent,args.message_id,args.text)
        elif args.command=='sequence-begin':
            if not args.attention_id:p.error('sequence-begin requires --attention-id')
            result=comp.begin(args.db,args.listener,args.attention_id,args.alternatives)
        elif args.command=='sequence-learn':
            if not args.attention_id:p.error('sequence-learn requires --attention-id')
            result=comp.learn(args.db,args.listener,args.agent,args.attention_id)
        elif args.command=='sequence-reference':
            result=comp.select(args.db,args.listener,args.agent,args.alternatives,args.after_seq,args.sequence_mode)
        elif args.command=='wayfinding-init':result=wf.initialize(args.db,args.seed)
        elif args.command=='wayfinding-status':result=wf.audit(args.db)
        elif args.command=='wayfinding-reconcile':
            result={'native':dev.reconcile(args.db,args.agent),'audit':wf.audit(args.db)}
        elif args.command in ('need-step','location-remember','location-coin','location-learn','location-receive','scout-observe','scout-send','follow-report'):
            if wf.audit(args.db)['pending']:raise ValueError('reconcile pending native experience first')
            if args.command=='need-step':result=wf.policy_step(args.db,args.agent,args.frozen)
            elif args.command=='location-remember':result=wf.remember_site(args.db,args.agent)
            elif args.command=='location-coin':result={'token':wf.coin_site(args.db,args.agent)}
            elif args.command=='location-learn':result=wf.learn_site(args.db,args.listener,args.agent,args.after_seq)
            elif args.command=='location-receive':result=wf.receive(args.db,args.listener,args.agent,args.after_seq)
            elif args.command=='scout-observe':result=wf.observe_source(args.db,args.agent)
            elif args.command=='scout-send':result=wf.send(args.db,args.agent,args.communication)
            else:
                report=wf.receive(args.db,args.listener,args.agent,args.after_seq)
                result=wf.acquire(args.db,args.listener,'water','drink',report,assigned=True)
        elif args.command=='symbol-init':result=symbols.initialize(args.db,args.seed)
        elif args.command=='community-init':result=community.initialize(args.db,args.seed)
        elif args.command=='community-status':result=community.audit(args.db)
        elif args.command=='recruit':result=community.recruit_newcomer(args.db,args.agent)
        elif args.command=='community-reconcile':
            result={'native':dev.reconcile(args.db,args.agent),
                    'memory':community.reconcile_budget(args.db,args.agent)}
        elif args.command=='status':result=dev.audit(args.db)
        elif args.command=='archive':result=dev.archive(args.db)
        elif args.command=='reconcile':result=dev.reconcile(args.db,args.agent)
        else:
            task_audit=(community.audit if args.command.startswith('community-') else dev.audit)(args.db)
            if task_audit['pending']:raise ValueError('reconcile pending experience before a new task')
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
                if args.command in ('demonstrate','community-demonstrate'):
                    token=symbols.coin(args.db,args.agent,args.target)
                    symbols.begin_attention(args.db,args.listener,args.alternatives)
                    deposited=dev.execute(args.db,args.agent,'deposit',[args.target],{'mass_kg':.001})
                    spoken=dev.execute(args.db,args.agent,'speak',parameters={'text':token})
                    feedback=(community if args.command=='community-demonstrate' else symbols).learn_attention(args.db,args.listener,args.agent)
                    result={'origin':'authored native deposit teaching scaffold','deposit':deposited,
                            'speech':spoken,'feedback':feedback}
                else:
                    before=dev.own_observation(args.db,args.listener)
                    seq=max((int(r['source_event_seq']) for r in before['audible_reports']),default=0)
                    token=symbols.production_token(args.db,args.agent,args.target)
                    spoken=dev.execute(args.db,args.agent,'speak',parameters={'text':token})
                    decision=(community if args.command=='community-reference' else symbols).select_reference(args.db,args.listener,args.agent,args.alternatives,seq)
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
