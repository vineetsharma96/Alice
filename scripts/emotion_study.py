"""Prospective F0-F3 native study; development and sealed confirmation separate."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import emotion_store as store, weather_store as weather
from underworld.weather_runtime import climate
from underworld.weather_tools import JournalWorld as SetupWorld, execute, walk, roof

HELDOUT=[17011,17021,17027,17033,17041]


def sources():
    paths=set(store.sources())
    paths.update(['scripts/emotion_study.py','scripts/emotion.py','emotion_tests/test_emotion.py',
                  'emotion_tests/test_viewer.py','underworld/emotion_viewer.py','underworld/web/emotion-panel.js',
                  'scripts/verify_emotion_viewer.mjs',
                  'docs/EMOTION_EVALUATION_PROTOCOL.md','docs/EMOTION_ARCHITECTURE.md',
                  'docs/EMOTION_UPSTREAM_AUDIT.md'])
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def force(path, temperature, rain, ident, enrolled=True):
    w=store.JournalWorld(path) if enrolled else SetupWorld(path)
    payload=dict(id=ident,observation_version=w.snapshot()['tick'],duration_s=1000,
                 temperature_c=temperature,rain_mm_h=rain,cloud_fraction=.9 if rain else 0,
                 wind_x_m_s=4 if rain else 0,wind_y_m_s=0)
    command=dict(kind='force',parameters=payload)
    return store.commit(path,command,ident) if enrolled else weather.commit(path,command)


def feed(w):
    """Explicit assigned native survival support for the conditioning experiment.

    Not autonomous success or natural development; no direct inventory/body edits.
    """
    walk(w,[2,3])
    for kind,target,need,action,duration in [('food','resource-1','hunger','eat',2),('water','resource-2','thirst','drink',1)]:
        for _ in range(10):
            body=w.observe_batch(['agent-1'])[0]['own_state']['body']
            if body[need]<.25:break
            gathered=execute(w,'gather',target,dict(mass_kg=.05))
            consumed=execute(w,action,parameters=dict(mass_kg=.05),duration=duration)
            if gathered['status']!='completed' or consumed['status']!='completed':raise ValueError('Assigned feeding failed')
        else:raise ValueError('Assigned feeding budget')


def rest(path, seconds):
    w=store.JournalWorld(path)
    for _ in range(int(seconds/10)):
        r=execute(w,'rest',duration=10)
        if r['status']!='completed':raise ValueError('Native rest failed')
        if max(w.observe_batch(['agent-1'])[0]['own_state']['body'][k] for k in ('hunger','thirst'))>.55:
            feed(w);walk(w,[4,6])


def probe(path, destination, temperature, rain=12):
    weather.save(path,destination)
    force(destination,temperature,rain,'probe-weather')
    start=time.perf_counter()
    result=store.commit(destination,dict(kind='emotion-policy',agent='agent-1'),'probe-choice')
    return dict(choice=result,wall_s=time.perf_counter()-start,world=str(destination.resolve().relative_to(ROOT)))


def bodily(folder,seed):
    result={}
    for label,temp,rain in [('cold',-10,12),('mild',24,0)]:
        src=folder/f'body-{label}-source.sqlite';path=folder/f'body-{label}.sqlite'
        weather.initialize(src,seed,1,climate(),True,food_kg=8,water_kg=16)
        store.attach(src,path);force(path,temp,rain,'body-condition')
        rest(path,150)
        stressed=store.inspect(path)
        force(path,24,0,'body-recovery');feed(store.JournalWorld(path));rest(path,100)
        recovered=store.inspect(path)
        result[label]=dict(distress=-stressed['people']['agent-1']['affect']['valence'],
                           recovery_distress=-recovered['people']['agent-1']['affect']['valence'],
                           health=recovered['snapshot']['entities'][4]['body']['health'],
                           replay=store.replay(path))
    result['passed']=result['cold']['distress']-result['mild']['distress']>=.1 and result['cold']['distress']-result['cold']['recovery_distress']>=.05
    return result


def run_seed(folder,seed):
    start=time.perf_counter();folder.mkdir(parents=True,exist_ok=False)
    source=folder/'assigned-setup.sqlite'
    weather.initialize(source,seed,1,climate(),True,food_kg=8,water_kg=16)
    force(source,24,0,'assigned-setup-weather',False)
    w=SetupWorld(source);roof(w);feed(w);walk(w,[4,6])
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    source_time=w.snapshot()['simulated_time_s']
    arms={}
    for mode in ('learned','frozen','disconnected','disabled'):
        path=folder/f'{mode}.sqlite';store.attach(source,path,mode=mode)
        force(path,-10,12,'conditioning-harm');rest(path,120)
        harm=store.inspect(path)['people']['agent-1']
        force(path,24,0,'conditioning-recovery');feed(store.JournalWorld(path));rest(path,260)
        feed(store.JournalWorld(path));walk(store.JournalWorld(path),[4,6])
        prior=store.inspect(path)
        temperature,rain={17011:(5,8),17021:(6,9),17027:(7,10),17033:(8,11),17041:(9,12)}.get(seed,(6,12))
        danger=probe(path,folder/f'{mode}-danger.sqlite',temperature,rain)
        harmless=probe(path,folder/f'{mode}-harmless.sqlite',24)
        # Own senses round temperature to whole degrees. 9.9 is perceived as10
        # and therefore is NOT the original chilly cue. 9.4 is perceived as9.
        force(path,9.4,12,'conditioning-reversal');rest(path,120)
        reversed_state=store.inspect(path)['people']['agent-1']
        force(path,24,0,'reversal-recovery');rest(path,260)
        feed(store.JournalWorld(path));walk(store.JournalWorld(path),[4,6])
        reversal=probe(path,folder/f'{mode}-reversal.sqlite',temperature,rain)
        final=store.inspect(path)
        arms[mode]=dict(harm=harm,prior=prior['people']['agent-1'],danger=danger,harmless=harmless,
                        reversed=reversed_state,reversal=reversal,final=final,
                        simulated_s=final['snapshot']['simulated_time_s']-source_time,
                        sqlite_bytes=path.stat().st_size,private_state_bytes=len(weather.dumps(final['people']).encode()),
                        replay=store.replay(path))
        if time.perf_counter()-start>600:raise ValueError('Per-seed wall budget reached')
    learned=arms['learned']
    changed=lambda r:r['choice']['influence']['changed']
    completed=lambda r:r['choice']['native']['receipt']['status']=='completed'
    action=lambda r:r['choice']['native']['choice']['action']
    gate=(changed(learned['danger']) and action(learned['danger'])=='move' and
          not changed(learned['harmless']) and action(learned['harmless'])=='rest' and
          not changed(learned['reversal']) and action(learned['reversal'])=='rest' and
          all(not changed(arms[m]['danger']) and action(arms[m]['danger'])=='rest' for m in ('frozen','disconnected','disabled')) and
          all(completed(a[p]) for a in arms.values() for p in ('danger','harmless','reversal')))
    return dict(seed=seed,arms=arms,behavior_gate=gate,bodily=bodily(folder,seed),wall_s=time.perf_counter()-start,
                assigned_setup_preserved=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['development','register','confirm']);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--registration',type=Path,default=ROOT/'artifacts/emotion_registration.json')
    p.add_argument('--workers',type=int,choices=[1,2],default=1,help='Independent worlds only; never parallel writers to one world')
    a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    if a.mode=='register':
        result=dict(seeds=HELDOUT,files=sources(),alice_base='8160e64389c086bd1049faad5a9a18a9ef4e242a')
        a.output.write_text(json.dumps(result,indent=2),encoding='utf8');return
    if a.mode=='confirm':
        registration=json.loads(a.registration.read_text(encoding='utf8'))
        if registration['files']!=sources() or registration['seeds']!=HELDOUT:raise ValueError('Unsealed confirmation source')
    start=time.perf_counter();rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(run_seed,a.folder/f'seed-{seed}',seed):seed for seed in (HELDOUT if a.mode=='confirm' else [53])}
        for future in as_completed(futures):
            row=future.result();rows.append(row)
            with gzip.open(a.folder/f"seed-{row['seed']}"/'measured-result.json.gz','wt',encoding='utf8') as stream:json.dump(row,stream,allow_nan=False)
            print(json.dumps(dict(seed=row['seed'],behavior_gate=row['behavior_gate'],bodily=row['bodily']['passed'],wall_s=row['wall_s'])),flush=True)
    rows.sort(key=lambda r:r['seed'])
    result=dict(mode=a.mode,files=sources(),seeds=rows,wall_s=time.perf_counter()-start,
                passed=sum(r['behavior_gate'] for r in rows)>= (4 if a.mode=='confirm' else 1) and all(r['bodily']['passed'] and r['assigned_setup_preserved'] for r in rows))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.suffix=='.gz':
        with gzip.open(a.output,'wt',encoding='utf8') as stream:json.dump(result,stream,allow_nan=False)
    else:a.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps(dict(passed=result['passed'],wall_s=result['wall_s'])))


if __name__=='__main__':main()
