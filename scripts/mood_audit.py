"""Independent F4 gates from native saves and analytic mood integration checks."""
from contextlib import closing
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import mood_store as store,weather_store as weather
from underworld.weather_runtime import load
from scripts.mood_study import SEEDS,sources


def audit_world(path,wanted):
    with closing(weather.connect(path)) as db:
        db.execute('BEGIN');final,final_policy,final_people,meta=store.head(db)
        w=load().World.restore(meta['initial'],final.snapshot()['run_id'])
        policies=json.loads(meta['policies']);people=json.loads(meta['people'])
        immutable={a:dict(p['temperament']) for a,p in people.items()}
        points=[];samples={};cold=None;warm=None;accepted=set();completed=set();rejected=[]
        for ident,raw,before,after,recorded in db.execute('SELECT logical_id,command,before_hash,after_hash,result FROM mood_operations ORDER BY seq'):
            if store.token(w,policies,people)!=before:raise ValueError('Native/private before chain mismatch')
            command=json.loads(raw);clock=w.snapshot()['simulated_time_s']
            if command['kind']=='force':
                if command['parameters']['id']=='actual-cold':cold=clock
                if command['parameters']['id']=='actual-recovery':warm=clock
            old={a:p['stress'] for a,p in people.items()};tick=int(w.snapshot()['tick'])
            actual=store.apply(w,policies,people,command,ident,lambda c:weather.apply(w,c,policies))
            if weather.dumps(actual)!=recorded or store.token(w,policies,people)!=after:raise ValueError('Replay result/head mismatch')
            w.check_invariants();dt=(int(w.snapshot()['tick'])-tick)*w.snapshot()['dt_s']
            for a,p in people.items():
                o=w.observe_batch([a])[0];body=o['own_state']['body'];thermal=o['own_state']['weather']['cold_burden']
                if p['temperament']!=immutable[a]:raise ValueError('Undeclared temperament mutation')
                if not body['alive']:raise ValueError('Death during F4 scenario')
                t=immutable[a];discomfort=max(body['hunger'],body['thirst'],.7*body['fatigue'],1-body['health'],thermal)
                target=min(1,max(0,t['sensitivity']*max(0,discomfort-.3)/.7))
                tau=t['rise_s'] if target>old[a] else t['recovery_s']
                expected=old[a] if p['mode']=='disabled' else target+(old[a]-target)*math.exp(-dt/tau)
                if abs(expected-p['stress'])>1e-12 or abs(p['mood']['valence']-max(-1,min(1,t['baseline']-expected)))>1e-12:
                    raise ValueError('Mood does not follow independently recomputed law')
                if not 0<=p['stress']<=1:raise ValueError('Mood outside finite bounds')
            p=people['agent-1'];points.append(dict(stress=p['stress'],before=old['agent-1'],dt_s=dt))
            for label,head in wanted.items():
                if after==head:
                    o=w.observe_batch(['agent-1'])[0]
                    samples[label]=dict(stress=p['stress'],time_s=w.snapshot()['simulated_time_s'],
                        thermal=o['own_state']['weather']['cold_burden'],
                        harmful=sum(e['harm']>.01 and e['intensity']>.01 for e in p['episodes']))
            n=actual['native']
            if command['kind']=='submit':
                if n['status']=='accepted':accepted.add(command['request']['request_id'])
                elif n['status']=='rejected':rejected.append(n)
            for r in w.observe_batch(['agent-1'])[0]['recent_action_results']:
                if r['status']=='completed' and r['request_id'] in accepted:completed.add(r['request_id'])
        if store.token(w,policies,people)!=store.token(final,final_policy,final_people):raise ValueError('Final head mismatch')
        if set(samples)!=set(wanted):raise ValueError('Missing actual sample head')
        for label,offset,start in [('cold40',40,cold),('cold120',120,cold),('warm210',210,warm),('warm900',900,warm)]:
            elapsed=samples[label]['time_s']-start
            if not offset<=elapsed<=offset+8:raise ValueError('Sample outside registered time window')
        if accepted!=completed or rejected:raise ValueError('Unfinished or rejected assigned action')
        snapshot=w.snapshot()
        if any(snapshot['boundary_sources_ug'].values()) or any(snapshot['operator_sources_ug'].values()):raise ValueError('Undeclared material input')
        for material in ('food','water'):
            if int(snapshot['material_totals_ug'][material])!=snapshot['initial_mass_ug'][material]:raise ValueError('Material ledger mismatch')
        physical=weather.replay(path)
        return dict(samples=samples,points=points,hash=store.token(w,policies,people),
                    native_hash=weather.digest(weather.dumps(snapshot)),accepted=len(accepted),completed=len(completed),rejected=len(rejected),
                    physical=physical,sqlite_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def audit(folder,raw,registration):
    if registration['files']!=sources() or registration['seeds']!=SEEDS or raw['files']!=registration['files']:raise ValueError('F4 source/seed seal mismatch')
    if [r['seed'] for r in raw['rows']]!=SEEDS:raise ValueError('Incomplete heldout inventory')
    start=time.perf_counter();rows=[];inventory={}
    for row in raw['rows']:
        base=folder/f"seed-{row['seed']}";arms={}
        for label in ('balanced','sensitive','disabled'):
            path=base/(label+'.sqlite')
            wanted={name:row['arms'][label][name]['hash'] for name in ('cold40','cold120','warm210','warm900')}
            proof=audit_world(path,wanted);arms[label]=proof
            inventory[str(path.resolve().relative_to(ROOT))]=proof['sqlite_sha256']
        a,b,d=arms['balanced'],arms['sensitive'],arms['disabled']
        active=(a,b)
        gates=dict(gradual=all(0<p['samples']['cold40']['stress']<.2 and p['samples']['cold120']['stress']>.15 and
                               all(v['stress']-v['before']<=.17+1e-12 for v in p['points'] if v['dt_s']<=10) for p in active),
                   temperament=b['samples']['cold120']['stress']-a['samples']['cold120']['stress']>=.1,
                   persists=all(p['samples']['warm210']['thermal']<.12 and p['samples']['warm210']['harmful']==0 and p['samples']['warm210']['stress']>.05 for p in active),
                   recovers=all(p['samples']['warm900']['stress']<.05 and p['samples']['warm900']['stress']<.25*p['samples']['cold120']['stress'] for p in active),
                   disabled=all(v['stress']==0 for v in d['points']),
                   physical_equal=len({p['native_hash'] for p in arms.values()})==1)
        copy=base/'balanced-mid-recovery.sqlite';resumed=store.inspect(copy)
        gates['resumed']=resumed['hash']==a['hash'] and store.replay(copy)['verified']
        inventory[str(copy.resolve().relative_to(ROOT))]=hashlib.sha256(copy.read_bytes()).hexdigest()
        source=base/'assigned-source.sqlite';weather.replay(source)
        initial_hash=weather.inspect(source)['state_hash']
        for label in arms:
            with closing(weather.connect(base/(label+'.sqlite'))) as db:
                meta=dict(db.execute('SELECT key,value FROM mood_meta'))
                if weather.digest(meta['initial'])!=initial_hash:raise ValueError('Source head no longer matches initial copy')
        inventory[str(source.resolve().relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
        if not all(gates.values()):raise ValueError('F4 gate failed from actual saves: '+str(gates))
        for p in arms.values():p.pop('points')
        rows.append(dict(seed=row['seed'],gates=gates,arms=arms));print(json.dumps(dict(seed=row['seed'],verified=True)),flush=True)
    historical={}
    for name in ['living_world_g_registration','developmental_h1_registration_repaired','developmental_h2_registration','h3_native_registration','h4_registration','h5_registration','gap_registration','weather_registration','emotion_registration']:
        r=json.loads((ROOT/f'artifacts/{name}.json').read_text(encoding='utf8'));pins=r.get('files',r.get('source_files'))
        if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in pins.items()):raise ValueError('Historical source drift: '+name)
        historical[name]=len(pins)
    return dict(verified=True,rows=rows,worlds=inventory,historical=historical,wall_s=time.perf_counter()-start,
                auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--raw',type=Path,default=ROOT/'artifacts/mood_f4_confirmation.json.gz')
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/mood_f4_registration.json')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    result=audit(a.folder,json.load(gzip.open(a.raw,'rt',encoding='utf8')),json.loads(a.registration.read_text(encoding='utf8')))
    a.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
