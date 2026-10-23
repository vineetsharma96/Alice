"""Independent new-gap verification from actual native saves and original source pins."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import adaptive as ad,context_teaching as ct,developmental as dev,storage  # noqa: E402
from scripts.adaptive_study import SEEDS,hashes  # noqa: E402


def read(path):
    raw=Path(path).read_bytes();return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def native(db,reported):
    ident=reported['request']['request_id']
    proof=dev._read(db,'development_records',ident,'id')
    if any(proof[k]!=reported[k] for k in ('request','receipt','native_events')):raise ValueError('gap trace/native receipt mismatch')
    before=int(proof['before']['own_state']['inventory_ug'].get('food',0))
    after=int(proof['after']['own_state']['inventory_ug'].get('food',0))
    if proof['food_gain_ug']!=after-before:raise ValueError('gap inventory gain mismatch')
    return proof


def world(path,reported):
    actual=ad.audit(path)
    if actual!=reported['audit'] or not storage.replay(path)['replay_matches']:raise ValueError('gap final private state/replay mismatch')
    snapshot=json.loads(dev.dumps(storage.inspect(path)))
    if snapshot!=reported['snapshot']:raise ValueError('gap final native snapshot mismatch')
    with closing(storage._connect(path,readonly=True)) as db:
        w,_,_,_=storage._head(db);w.check_invariants()
        if db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]:raise ValueError('unexpected gap model use')
    return actual


def audit(study,registration):
    report=read(study);pins=read(registration)
    if report['development'] or [r['seed'] for r in report['runs']]!=SEEDS:raise ValueError('exact gap confirmation cohort required')
    if hashes()!=report['files'] or hashes()!=pins['files']:raise ValueError('new gap source registration mismatch')
    old={}
    for name in ['living_world_g_registration','developmental_h1_registration_repaired','developmental_h2_registration','h3_native_registration','h4_registration','h5_registration']:
        m=read(ROOT/'artifacts'/f'{name}.json');files=m.get('files',m.get('source_files'))
        old[name]=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in files.items())
    if not all(old.values()):raise ValueError('historical source changed')
    online_totals={m:0 for m in ('adaptive','legacy','frozen','memory','authored')}
    far_attempts=dict(online_totals);brier={m:[] for m in online_totals};cooperation_totals={m:0 for m in ('learned','muted','scrambled','whole')}
    per_seed=[];durations=[];errors={m:[] for m in online_totals};new_requests=0;teaching_updates=dict(enabled=0,muted=0)
    for run in report['runs']:
        seed=run['seed'];directory=Path(run.get('directory',Path('data')/'gap-confirmation-20261021'))
        if set(run['online'])!=set(online_totals) or set(run['arms'])!=set(cooperation_totals):raise ValueError('missing gap controls')
        for mode,case in run['online'].items():
            path=directory/f'{seed}-online-{mode}.sqlite';world(path,case['final'])
            successes=attempts=0;losses=[]
            with closing(storage._connect(path,readonly=True)) as db:
                if len(case['heldout'])!=6 or len(case['far_transfer'])!=6:raise ValueError('missing gap online opportunities')
                for trial in case['training']+[t['experience'] for t in case['far']]:native(db,trial)
                for label,trials in [(1,case['heldout']),(0,case['far_transfer'])]:
                    for t in trials:
                        e=native(db,t['experience']);gather=e['request']['action_type']=='gather'
                        actual=e['receipt']['status']=='completed' and e['food_gain_ug']>0
                        if label:
                            if t['success']!=actual:raise ValueError('reported gap food goal not achieved')
                            successes+=actual
                        else:
                            attempts+=gather
                            if gather and e['receipt']['error_code']!='OUT_OF_REACH':raise ValueError('far opportunity lacks actual native reach rejection')
                            if t['attempted']!=gather:raise ValueError('gap far attempt mislabeled')
                        probability=t['probability']
                        if not 0<=probability<=1:raise ValueError('invalid prediction probability')
                        losses.append((probability-label)**2)
                receipts=[json.loads(r[0])['receipt'] for r in db.execute("SELECT payload FROM development_records WHERE kind='experience'")]
                errors[mode].extend(r['error_code'] or r['status'] for r in receipts if r['status']!='completed')
            if successes!=case['successes'] or attempts!=case['far_attempts'] or abs(sum(losses)/12-case['brier'])>1e-10:raise ValueError('gap online aggregate mismatch')
            online_totals[mode]+=successes;far_attempts[mode]+=attempts;brier[mode].append(case['brier'])
        base=directory/f'{seed}-training.sqlite';world(base,run['training']['final'])
        with closing(storage._connect(directory/f'{seed}-setup.sqlite',readonly=True)) as db:base_requests=db.execute("SELECT COUNT(*) FROM development_records WHERE kind='experience'").fetchone()[0]
        heads={c['initial_head'] for c in run['arms'].values()}
        if len(heads)!=1 or storage.inspect(directory/f'{seed}-setup.sqlite')['state_hash'] not in heads:raise ValueError('gap arm starting heads differ')
        outcomes={}
        for mode,case in run['arms'].items():
            if not case.get('fresh_process'):raise ValueError('gap scoring lacks fresh-process continuation')
            path=directory/f'{seed}-{mode}.sqlite';world(path,case['final'])
            drank=gathered=False
            with closing(storage._connect(path,readonly=True)) as db:
                for x in case['steps']:
                    e=native(db,x['experience'])
                    r=dev._read(db,'development_records',x['result']['record_id'],'id')
                    if dict(r,record_id=x['result']['record_id'])!=x['result']:raise ValueError('gap plan result differs from own durable frame')
                    if e['receipt']['status']!='completed':raise ValueError('gap cooperation native rejection')
                    if x['role']=='gather':
                        gathered=e['request']['target_ids']==[run['operator_target']] and e['receipt']['status']=='completed'
                    if x['goal_completed']:
                        relief=e['before']['own_state']['body']['thirst']-e['after']['own_state']['body']['thirst']
                        drank=e['request']['action_type']=='drink' and e['receipt']['observable_effects'].get('description')=='ingested_ug=50000000' and relief>0
                count=db.execute("SELECT COUNT(*) FROM development_records WHERE kind='experience'").fetchone()[0]
                new_requests+=count-base_requests
            actual=drank and gathered
            if case['success']!=actual:raise ValueError('gap location goal differs from actual remote acquisition/relief')
            cooperation_totals[mode]+=actual;outcomes[mode]=actual
            durations.append(dict(seed=seed,mode=mode,start_sim_s=case['initial_sim_s'],end_sim_s=case['final']['snapshot']['simulated_time_s'],wall_s=case['wall_s']))
        per_seed.append(dict(seed=seed,cooperation=outcomes,wall_s=run['wall_s']))
        for mode,case in run['teaching'].items():
            path=Path(case['path']);world(path,case['final']);ct.audit(path)
            count=0
            with closing(storage._connect(path,readonly=True)) as db:
                for t in case['trials']:
                    if t['after']['learned']:
                        p=t['after']['proof'];actual=dev._read(db,'development_records',p['record_id'],'id')
                        if dict(actual,record_id=p['record_id'])!=p:raise ValueError('context learning proof mismatch')
                        native(db,t['action']['deposit']);native(db,t['action']['speech']);count+=1
            if count!=case['updates']:raise ValueError('context teaching count mismatch')
            if mode=='enabled' and not case['quiet_after_disclosure']:raise ValueError('disclosure model did not affect behavior')
            teaching_updates[mode]+=count
    online_gate=online_totals['adaptive']>=27 and online_totals['adaptive']-online_totals['legacy']>=9 and far_attempts['adaptive']<=15 and far_attempts['adaptive']<=far_attempts['frozen']/2
    location_gate=cooperation_totals['learned']==5 and all(cooperation_totals['learned']-cooperation_totals[m]>=2 for m in ('muted','scrambled','whole'))
    if (report['online_totals'],report['far_attempts'],report['cooperation_totals'],report['online_gate'],report['location_gate'])!=(online_totals,far_attempts,cooperation_totals,online_gate,location_gate):raise ValueError('gap gate recomputation mismatch')
    teaching_gate=teaching_updates==dict(enabled=10,muted=0)
    if report['teaching_updates']!=teaching_updates or report['teaching_gate']!=teaching_gate:raise ValueError('context teaching gate mismatch')
    return dict(verified=True,online_gate=online_gate,location_gate=location_gate,online_totals=online_totals,far_attempts=far_attempts,
        mean_prequential_brier={m:sum(x)/len(x) for m,x in brier.items()},online_native_rejections=errors,cooperation_totals=cooperation_totals,teaching_updates=teaching_updates,teaching_gate=teaching_gate,
        native_scored_cooperation_requests=new_requests,per_seed=per_seed,durations=durations,
        old_source_registrations_match=old,wall_s=report['wall_s'],model_calls=0,
        scope='authored feature/geometry/motor/need/reporting priors; narrow transfer, not learned grammar or semantic calibration')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/gap_registration.json');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=audit(args.study,args.registration);args.output.write_text(json.dumps(r,indent=2),encoding='utf8')
    print(json.dumps({k:r[k] for k in ('verified','online_gate','location_gate','online_totals','far_attempts','cooperation_totals')}))


if __name__=='__main__':main()
