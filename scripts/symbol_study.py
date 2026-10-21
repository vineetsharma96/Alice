"""Conditional H2: private coined tokens, native demonstrations and reference actions."""
import argparse
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import developmental as dev, symbols, storage, planning  # noqa: E402
from developmental_study import introduce, identifier, interval, SEEDS  # noqa: E402

ARMS=['learned','silence','shuffled','random','oracle']


def move_listener(path):
    destination=[3,3]
    for _ in range(32):
        o=dev.own_observation(path,'agent-2')
        if math.dist(o['own_state']['position_m'],destination)<.05:return
        point=planning._route(o,destination)
        if not point:raise ValueError('authored hearing-station setup route blocked')
        distance=math.dist(o['own_state']['position_m'],point)
        r=dev.execute(path,'agent-2','move',parameters={'x_m':point[0],'y_m':point[1]},duration=max(1,math.ceil(distance)))
        if r['receipt']['status']!='completed':raise ValueError('native hearing-station movement failed')
    raise ValueError('hearing-station setup exceeded declared motion bound')


def tray(path,rng):
    positions=[[1,3],[2,2],[3,3]]
    rng.shuffle(positions)
    classes=[('food',.05),('food',.25),('water',.05)]
    ids=[]
    for (material,mass),position in zip(classes,positions):
        ident=identifier(rng);introduce(path,ident,material,mass,position);ids.append(ident)
    return ids


def train(path,seed):
    start=time.perf_counter();symbols.initialize(path,seed)
    move_listener(path)
    for target in ('resource-1','resource-2'):
        result=dev.execute(path,'agent-1','gather',[target],{'mass_kg':.1})
        assert result['receipt']['status']=='completed'
    rng=random.Random(seed+300)
    candidates=tray(path,rng)
    sequence=list(range(3))*12;rng.shuffle(sequence)
    trials=[]
    for class_index in sequence:
        if time.perf_counter()-start>240:raise TimeoutError('registered seed compute cap')
        target=candidates[class_index]
        token=symbols.coin(path,'agent-1',target)
        symbols.begin_attention(path,'agent-2',candidates)
        deposited=dev.execute(path,'agent-1','deposit',[target],{'mass_kg':.001})
        assert deposited['receipt']['status']=='completed'
        spoken=dev.execute(path,'agent-1','speak',parameters={'text':token})
        assert spoken['receipt']['status']=='completed'
        learned=symbols.learn_attention(path,'agent-2','agent-1')
        trials.append({'operator_assigned_target':target,'class_index_operator_only':class_index,
                       'deposit':deposited,'speech':spoken,'listener_feedback':learned})
    return {'path':str(path),'trials':trials,'audit':symbols.audit(path),
            'wall_s':time.perf_counter()-start,'snapshot':storage.inspect(path),
            'origin':'authored physical demonstrations; not autonomous teaching'}


def evaluate(path,seed,arm):
    start=time.perf_counter();initial=symbols.audit(path);before=storage.inspect(path)
    rng=random.Random(seed+400)
    sequence=list(range(3))*4;rng.shuffle(sequence)
    shuffled=list(sequence);random.Random(seed+500).shuffle(shuffled)
    trials=[]
    for i,class_index in enumerate(sequence):
        if time.perf_counter()-start>240:raise TimeoutError('registered evaluation cap')
        ids=tray(path,rng)
        target=ids[class_index]
        alternatives=list(ids);rng.shuffle(alternatives)
        previous=dev.own_observation(path,'agent-2')
        seq=max((int(r['source_event_seq']) for r in previous['audible_reports']),default=0)
        emitted=None
        if arm=='silence':
            spoken=dev.execute(path,'agent-1','rest')
        else:
            emitted=symbols.production_token(path,'agent-1',ids[shuffled[i]] if arm=='shuffled' else target)
            spoken=dev.execute(path,'agent-1','speak',parameters={'text':emitted})
        if arm=='oracle':
            # Explicitly privileged comparator, never a learner/dictionary update.
            report=symbols._heard(dev.own_observation(path,'agent-2'),'agent-1',seq)
            decision={'target':target,'message':report,'origin':'privileged_target_oracle_upper_comparator'}
        else:
            decision=symbols.select_reference(path,'agent-2','agent-1',alternatives,seq,
                'silence' if arm=='silence' else 'random' if arm=='random' else 'learned')
        inspected=dev.execute(path,'agent-2','inspect',[decision['target']],update_memory=False)
        effect=inspected['receipt']['observable_effects'].get('description','')
        actual=effect.split(':')[0] if inspected['receipt']['status']=='completed' else None
        success=actual==target
        trials.append({'trial':i,'intended_target_operator_only':target,
            'candidate_ids':alternatives,'emitted_token':emitted,'speech_or_rest':spoken,
            'decision':decision,'inspection':inspected,'actual_target':actual,'success':success})
    final=symbols.audit(path)
    assert initial['vocabulary_hashes']==final['vocabulary_hashes'],'scored vocabularies must be frozen'
    with closing(storage._connect(path,readonly=True)) as db:
        world,_,_,_=storage._head(db);world.check_invariants()
    return {'seed':seed,'arm':arm,'path':str(path),'trials':trials,'successes':sum(t['success'] for t in trials),
        'rate':sum(t['success'] for t in trials)/12,'initial_head':before['state_hash'],
        'initial_vocabulary_hashes':initial['vocabulary_hashes'],'final_vocabulary_hashes':final['vocabulary_hashes'],
        'initial_simulated_s':before['simulated_time_s'],'final_snapshot':storage.inspect(path),
        'wall_s':time.perf_counter()-start,'replay':storage.replay(path),'model_calls':0,
        'scored_updates':0,'native_invariants':True,'audit':final}


def seed_case(directory,seed):
    start=time.perf_counter();world=directory/f'{seed}-training.sqlite';training=train(world,seed)
    arms=[]
    for arm in ARMS:
        if time.perf_counter()-start>240:raise TimeoutError('registered whole-seed cap')
        path=directory/f'{seed}-{arm}.sqlite';storage.save(world,'branch-'+arm,path)
        if arm=='learned':
            output=directory/f'{seed}-learned.json'
            child=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--evaluate','--db',str(path),
                '--seed',str(seed),'--arm',arm,'--output',str(output)],cwd=ROOT,capture_output=True,text=True,timeout=240)
            if child.returncode:raise RuntimeError(child.stderr)
            result=json.loads(output.read_text(encoding='utf-8'));result['fresh_process']=True
        else:result=evaluate(path,seed,arm)
        arms.append(result)
        print(json.dumps({'seed':seed,'arm':arm,'rate':result['rate'],'wall_s':result['wall_s']}),flush=True)
    assert len({r['initial_head'] for r in arms})==1
    assert len({dev.digest(r['initial_vocabulary_hashes']) for r in arms})==1
    learned=arms[0];shuffled=next(a for a in arms if a['arm']=='shuffled')
    swaps=[{'trial':a['trial'],'tokens':[a['emitted_token'],b['emitted_token']],
            'selected':[a['actual_target'],b['actual_target']],
            'response_changed':a['actual_target']!=b['actual_target']}
           for a,b in zip(learned['trials'],shuffled['trials']) if a['emitted_token']!=b['emitted_token']]
    result={'seed':seed,'training':training,'arms':arms,'token_swap_counterfactuals':swaps,
            'wall_s':time.perf_counter()-start,'matched_initial_heads':True,
            'lifetimes':'one trained life plus explicitly labelled counterfactual branches'}
    (directory/f'{seed}-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def summary(cases):
    rates={a:sum(next(r['rate'] for r in c['arms'] if r['arm']==a) for c in cases)/len(cases) for a in ARMS}
    improved={a:sum(next(r['rate'] for r in c['arms'] if r['arm']=='learned')>
                        next(r['rate'] for r in c['arms'] if r['arm']==a) for c in cases) for a in ('silence','shuffled')}
    swaps=sum(s['response_changed'] for c in cases for s in c['token_swap_counterfactuals'])
    invariants=all(c['matched_initial_heads'] and all(r['replay']['replay_matches'] and r['scored_updates']==0 and
        r['native_invariants'] and r['initial_vocabulary_hashes']==r['final_vocabulary_hashes'] and
        r['model_calls']==0 for r in c['arms']) and c['arms'][0].get('fresh_process') for c in cases)
    gate=(rates['learned']>=.75 and all(rates['learned']-rates[a]>=.2 and improved[a]>=min(4,len(cases))
          for a in ('silence','shuffled')) and swaps>0 and invariants)
    return {'rates':rates,'improved_seeds':improved,'causal_token_response_changes':swaps,
            'invariants':bool(invariants),'h2_gate':bool(gate),
            'wilson_intervals':{a:interval(sum(next(r['successes'] for r in c['arms'] if r['arm']==a) for c in cases),12*len(cases)) for a in ARMS},
            'interpretation':'Scaffolded, one-token naming protocol over three authored sensory classes; no human language or spontaneous intention claim.'}


def register(output):
    files=['underworld/developmental.py','underworld/symbols.py','scripts/developmental_study.py',
           'scripts/symbol_study.py','tests/test_symbols.py','config/developmental.toml',
           'docs/DEVELOPMENTAL_H2_PROTOCOL.md','docs/DEVELOPMENTAL_PROTOCOL.md']
    output.write_text(json.dumps({'confirmation_seeds':SEEDS,'files':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}},indent=2)+'\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluate',action='store_true');p.add_argument('--db',type=Path)
    p.add_argument('--seed',type=int);p.add_argument('--arm',choices=ARMS)
    p.add_argument('--split',choices=('development','confirmation'))
    p.add_argument('--directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path)
    args=p.parse_args()
    if args.evaluate:
        if not args.db or args.seed is None or not args.arm:p.error('evaluation requires existing db, seed and arm')
        result=evaluate(args.db,args.seed,args.arm)
    else:
        h1=json.loads((ROOT/'artifacts/developmental_h1_confirmation_repaired.json').read_text(encoding='utf-8'))
        if not h1['summary']['h1_gate']:raise ValueError('H1 gate has not passed; H2 promotion forbidden')
        h1_source=json.loads((ROOT/'artifacts/developmental_h1_registration_repaired.json').read_text(encoding='utf-8'))
        assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in h1_source['files'].items())
        if not args.split or not args.directory:p.error('new study requires split and new directory')
        if args.split=='confirmation':
            if not args.registration:p.error('confirmation requires prospective source registration')
            spec=json.loads(args.registration.read_text(encoding='utf-8'));assert spec['confirmation_seeds']==SEEDS
            assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in spec['files'].items())
        args.directory=args.directory.resolve();args.directory.mkdir(parents=True,exist_ok=False)
        start=time.perf_counter();cases=[]
        for seed in ([41] if args.split=='development' else SEEDS):
            if time.perf_counter()-start>1800:raise TimeoutError('registered study compute cap')
            cases.append(seed_case(args.directory,seed))
            args.output.write_text(json.dumps({'split':args.split,'cases':cases},indent=2)+'\n',encoding='utf-8')
        result={'split':args.split,'cases':cases,'summary':summary(cases),'wall_s':time.perf_counter()-start}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if 'summary' in result:print(json.dumps(result['summary'],indent=2))


if __name__=='__main__':main()
