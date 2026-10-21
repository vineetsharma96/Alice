"""New bounded H0-H5 gap experiments; old failures and policies stay unchanged."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import adaptive as ad, context_teaching as ct, developmental as dev, storage, wayfinding as wf  # noqa: E402
from scripts.developmental_study import introduce, identifier  # noqa: E402

SEEDS=[11003,11027,11047,11057,11071]
SITES=[[14,3],[3,14],[14,14]]
HUB=[25,25]
SOURCES=['underworld/adaptive.py','scripts/adaptive_study.py','tests/test_adaptive.py','docs/DEVELOPMENTAL_GAP_PROTOCOL.md',
         'scripts/adaptive_continuity.py','scripts/adaptive_audit.py','scripts/adaptive_learner.py',
         'underworld/adaptive_panel.py','underworld/web/adaptive.html','underworld/web/adaptive.js',
         'tests/test_adaptive_surfaces.py','scripts/verify_adaptive_panel.mjs',
         'underworld/context_teaching.py','tests/test_context_teaching.py']


def hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


def finish(path):
    audit=ad.audit(path);snapshot=storage.inspect(path)
    with closing(storage._connect(path,readonly=True)) as db:
        world,_,_,_=storage._head(db);world.check_invariants()
        calls=db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
        receipts=[json.loads(r[0])['receipt'] for r in db.execute("SELECT payload FROM development_records WHERE kind='experience'")]
    return dict(snapshot=snapshot,audit=audit,replay=storage.replay(path),model_calls=calls,
                native_rejections=[r['error_code'] or r['status'] for r in receipts if r['status']!='completed'])


def online(path,seed,mode):
    ad.initialize(path,seed);rng=random.Random(seed)
    introduce(path,'reachable','food',.05,[1,3]);introduce(path,'ambiguous-range','food',.05,[3.6,3])
    training=[]
    for _ in range(3):
        e=dev.execute(path,'agent-1','gather',['reachable'],{'mass_kg':.001},learn_food=mode in ('legacy','memory'))
        if mode=='adaptive':ad.learn_outcome(path,'agent-1',e['request']['request_id'])
        training.append(e)
    trials=[]
    for i,target in enumerate(['ambiguous-range']*5):
        d=(ad.choose(path,'agent-1',[target]) if mode=='adaptive' else dev.choose(path,'agent-1',[target],
            mode={'legacy':'learning','frozen':'frozen','memory':'memory','authored':'authored'}[mode]))
        e=dev.execute(path,'agent-1','gather',[d['target']],{'mass_kg':.001},learn_food=mode in ('legacy','memory'),prediction=d) if d['target'] else dev.execute(path,'agent-1','rest',update_memory=False)
        if mode=='adaptive' and d['target']:ad.learn_outcome(path,'agent-1',e['request']['request_id'])
        trials.append(dict(decision=d,experience=e))
    heldout=[]
    for distance in [.9,1.1,1.3]*2:
        ident=identifier(rng);introduce(path,ident,'food',.02,[2+distance,3])
        d=(ad.choose(path,'agent-1',[ident]) if mode=='adaptive' else dev.choose(path,'agent-1',[ident],
            mode={'legacy':'learning','frozen':'frozen','memory':'memory','authored':'authored'}[mode]))
        probability=d['predictions'][0].get('probability',d['predictions'][0].get('mean'))
        e=dev.execute(path,'agent-1','gather',[d['target']],{'mass_kg':.001},learn_food=mode in ('legacy','memory'),prediction=d) if d['target'] else dev.execute(path,'agent-1','rest',update_memory=False)
        if mode=='adaptive' and d['target']:ad.learn_outcome(path,'agent-1',e['request']['request_id'])
        heldout.append(dict(operator_target=ident,decision=d,experience=e,probability=probability,success=e['food_gain_ug']>0))
    far_transfer=[]
    for distance in [1.7,1.8,1.9]*2:
        ident=identifier(rng);introduce(path,ident,'food',.02,[2+distance,3])
        d=(ad.choose(path,'agent-1',[ident]) if mode=='adaptive' else dev.choose(path,'agent-1',[ident],
            mode={'legacy':'learning','frozen':'frozen','memory':'memory','authored':'authored'}[mode]))
        probability=d['predictions'][0].get('probability',d['predictions'][0].get('mean'))
        e=dev.execute(path,'agent-1','gather',[d['target']],{'mass_kg':.001},learn_food=mode in ('legacy','memory'),prediction=d) if d['target'] else dev.execute(path,'agent-1','rest',update_memory=False)
        if mode=='adaptive' and d['target']:ad.learn_outcome(path,'agent-1',e['request']['request_id'])
        far_transfer.append(dict(operator_target=ident,decision=d,experience=e,probability=probability,attempted=bool(d['target'])))
    return dict(mode=mode,training=training,far=trials,heldout=heldout,successes=sum(x['success'] for x in heldout),
                far_transfer=far_transfer,far_attempts=sum(x['attempted'] for x in far_transfer),
                brier=(sum((x['probability']-1)**2 for x in heldout)+sum(x['probability']**2 for x in far_transfer))/12,final=finish(path))


def relief(path,agent):
    # Authored warm-up, physical supplies and outcomes, no need intervention.
    for source,action in [('resource-1','eat'),('resource-2','drink')]:
        g=dev.execute(path,agent,'gather',[source],{'mass_kg':.05},update_memory=False)
        c=dev.execute(path,agent,action,parameters={'mass_kg':.05},duration=2 if action=='eat' else 1,update_memory=False)
        wf.learn_relief(path,agent,g['request']['request_id'],c['request']['request_id'])


def train_locations(path,seed):
    ad.initialize(path,seed)
    wf.walk(path,'agent-4',[28,28]);wf.walk(path,'agent-3',[29,28])
    wf.walk(path,'agent-2',[3,3]);relief(path,'agent-2')
    for source in ('resource-1','resource-2'):
        dev.execute(path,'agent-1','gather',[source],{'mass_kg':.02},update_memory=False)
    rng=random.Random(seed+100);lessons=[];ids=[]
    for i,site in enumerate(SITES):
        wf.walk(path,'agent-1',site);ad.refresh(path,'agent-1',True)
        # Separate nearby positions, same personally perceived cell.
        wf.walk(path,'agent-2',[site[0]-1,site[1]])
        ad.refresh(path,'agent-2',True)
        local=[]
        for kind in (('food','water') if i<2 else ('food',)):
            target=identifier(rng);introduce(path,target,kind,.01,site);local.append(target);ids.append(target)
        ad.refresh(path,'agent-1')
        for repeat in range(2):
            for target in local:
                attention=f'loc-{i}-{repeat}-{target}'
                text=ad.encode_location(path,'agent-1',target,True)
                ad.begin_location(path,'agent-2',attention,local)
                e=dev.execute(path,'agent-1','deposit',[target],{'mass_kg':.001},update_memory=False)
                if e['receipt']['status']!='completed':raise ValueError('location teaching deposit failed')
                speech=ad.perform(path,'agent-1',attention,'speak',parameters={'text':text},duration=2)
                learned=ad.learn_location(path,'agent-2','agent-1',attention)
                lessons.append(dict(deposit=e,speech=speech,learning=learned))
    wf.walk(path,'agent-2',HUB);wf.walk(path,'agent-1',[24,25])
    return dict(lessons=lessons,ids=ids,final=finish(path))


def prepare(path,seed,depleted=False):
    target=identifier(random.Random(seed+200))
    introduce(path,target,'water',.05,SITES[2])
    wf.walk(path,'agent-1',SITES[2]);ad.refresh(path,'agent-1')
    if depleted:
        wf.walk(path,'agent-3',[13,14])
        e=dev.execute(path,'agent-3','gather',[target],{'mass_kg':.05},update_memory=False)
        if e['receipt']['status']!='completed':raise ValueError('native depletion failed')
        wf.walk(path,'agent-3',[29,28])
    wf.walk(path,'agent-1',[24,25])
    return target


def cooperation(path,mode):
    start=time.perf_counter();initial=storage.inspect(path)
    h=ad.private(path,'agent-1','agent-1');source=max((s for s in h['sources'].values() if s['mass_ug']>=50000000),key=lambda s:s['tick'])
    if mode=='learned':speech=ad.share_step(path,'agent-1')
    elif mode=='muted':speech=dev.execute(path,'agent-1','rest',update_memory=False)
    elif mode=='scrambled':
        text=ad.encode_location(path,'agent-1',source['entity_id'])
        state=ad.private(path,'agent-1','agent-1')
        actual='site:'+source['cell'];other=next(v['token'] for k,v in state['production'].items() if k.startswith('site:') and k!=actual)
        text=' '.join(other if t==state['production'][actual]['token'] else t for t in text.split())
        speech=ad.perform(path,'agent-1','scored-report','speak',parameters={'text':text},duration=2)
    else:
        speech=ad.share_step(path,'agent-1')
    steps=[]
    for _ in range(40):
        x=ad.step(path,'agent-2',mode='whole' if mode=='whole' else 'muted' if mode=='muted' else 'learned')
        steps.append(x)
        if x['goal_completed'] or x['role'] in ('scarcity','idle'):break
    final=finish(path)
    correct_gather=any(x['role']=='gather' and x['experience']['request']['target_ids']==[source['entity_id']] and x['experience']['receipt']['status']=='completed' for x in steps)
    return dict(mode=mode,speech=speech,steps=steps,success=correct_gather and any(x['goal_completed'] and x['experience']['request']['action_type']=='drink' for x in steps),
                initial_head=initial['state_hash'],initial_sim_s=initial['simulated_time_s'],
                final=final,wall_s=time.perf_counter()-start)


def teaching_case(directory,seed):
    base=directory/f'{seed}-teaching-base.sqlite';ad.initialize(base,seed)
    wf.walk(base,'agent-2',[3,3]);ct.attach(base,['agent-1','agent-2'])
    for target in ('resource-1','resource-2'):dev.execute(base,'agent-1','gather',[target],{'mass_kg':.01},update_memory=False)
    head=storage.inspect(base)['state_hash'];arms={}
    for mode in ('enabled','muted'):
        path=directory/f'{seed}-teaching-{mode}.sqlite';storage.save(base,'teaching-'+mode,path);trials=[]
        for _ in range(2):
            before=ct.observe(path,'agent-2')
            action=ct.teacher_step(path,'agent-1') if mode=='enabled' else dev.execute(path,'agent-1','rest',duration=3,update_memory=False)
            after=ct.observe(path,'agent-2');trials.append(dict(before=before,action=action,after=after))
        quiet=not ct.teacher_step(path,'agent-1')['taught'] if mode=='enabled' else None
        ct.audit(path)
        arms[mode]=dict(path=str(path),initial_head=head,trials=trials,updates=sum(t['after']['learned'] for t in trials),
                       quiet_after_disclosure=quiet,final=finish(path))
    return arms


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['register','run','evaluate'])
    p.add_argument('--directory',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/gap_registration.json')
    p.add_argument('--db',type=Path);p.add_argument('--mode',choices=['learned','muted','scrambled','whole'])
    p.add_argument('--development',action='store_true');args=p.parse_args();start=time.perf_counter()
    if args.command=='register':result=dict(seeds=SEEDS,development=[53],files=hashes(),written_utc=time.time())
    elif args.command=='evaluate':result=cooperation(args.db,args.mode)
    else:
        if not args.development and json.loads(args.registration.read_text(encoding='utf8'))['files']!=hashes():raise ValueError('gap registration mismatch')
        args.directory.mkdir(parents=True,exist_ok=False);runs=[]
        for seed in ([53] if args.development else SEEDS):
            seed_start=time.perf_counter();online_results={}
            for mode in ('adaptive','legacy','frozen','memory','authored'):
                online_results[mode]=online(args.directory/f'{seed}-online-{mode}.sqlite',seed,mode)
            base=args.directory/f'{seed}-training.sqlite';training=train_locations(base,seed)
            setup=args.directory/f'{seed}-setup.sqlite';storage.save(base,'setup',setup);target=prepare(setup,seed)
            arms={}
            for mode in ('learned','muted','scrambled','whole'):
                path=args.directory/f'{seed}-{mode}.sqlite';storage.save(setup,mode,path)
                output=args.directory/f'{seed}-{mode}.json'
                subprocess.run([sys.executable,__file__,'evaluate','--db',str(path),'--mode',mode,'--output',str(output)],cwd=ROOT,check=True,timeout=120)
                arms[mode]=json.loads(output.read_text(encoding='utf8'))
                arms[mode]['fresh_process']=True
            teaching=teaching_case(args.directory,seed)
            runs.append(dict(seed=seed,directory=str(args.directory.resolve()),online=online_results,training=training,operator_target=target,arms=arms,teaching=teaching,wall_s=time.perf_counter()-seed_start))
            print(json.dumps(dict(seed=seed,online={m:r['successes'] for m,r in online_results.items()},cooperation={m:r['success'] for m,r in arms.items()},wall_s=runs[-1]['wall_s'])),flush=True)
            if runs[-1]['wall_s']>400 or time.perf_counter()-start>2400:raise TimeoutError('gap study compute cap')
        online_totals={m:sum(r['online'][m]['successes'] for r in runs) for m in runs[0]['online']}
        far_attempts={m:sum(r['online'][m]['far_attempts'] for r in runs) for m in runs[0]['online']}
        cooperation_totals={m:sum(r['arms'][m]['success'] for r in runs) for m in runs[0]['arms']}
        teaching_updates={m:sum(r['teaching'][m]['updates'] for r in runs) for m in ('enabled','muted')}
        n=len(runs)
        result=dict(development=args.development,files=hashes(),runs=runs,online_totals=online_totals,far_attempts=far_attempts,teaching_updates=teaching_updates,
            cooperation_totals=cooperation_totals,online_gate=online_totals['adaptive']>=n*5.4 and online_totals['adaptive']-online_totals['legacy']>=n*1.8 and far_attempts['adaptive']<=n*3 and far_attempts['adaptive']<=far_attempts['frozen']/2,
            location_gate=cooperation_totals['learned']==n and all(cooperation_totals['learned']-cooperation_totals[m]>=n*.4 for m in ('muted','scrambled','whole')),
            teaching_gate=teaching_updates['enabled']==n*2 and teaching_updates['muted']==0 and all(r['teaching']['enabled']['quiet_after_disclosure'] for r in runs),
            wall_s=time.perf_counter()-start)
    if args.output.exists():raise ValueError('refuse overwriting gap evidence')
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k in ('online_totals','cooperation_totals','online_gate','location_gate','wall_s')}))


if __name__=='__main__':main()
