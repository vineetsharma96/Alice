"""Prospective F4 native mood curves, paired temperaments and exact recovery resume."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
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
from underworld import mood_store as store,weather_store as weather
from underworld.weather_runtime import climate
from underworld.weather_tools import JournalWorld as WeatherWorld,execute

SEEDS=[18101,18121,18127,18143,18149]


def sources():
    paths=set(store.sources())|{'scripts/mood.py','scripts/mood_study.py','docs/MOOD_F4_PROTOCOL.md','mood_tests/test_mood.py','mood_tests/test_viewer.py','scripts/verify_mood_viewer.mjs'}
    # Observer files are included when present, before final source registration.
    paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'underworld').glob('mood_viewer.py'))
    paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'underworld/web').glob('mood-panel.*'))
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def feed(w):
    """Assigned real finite-stock feeding; no body or mood edits, never policy credit."""
    for need,resource,action,duration in [('hunger','resource-1','eat',2),('thirst','resource-2','drink',1)]:
        for _ in range(8):
            if w.observe_batch(['agent-1'])[0]['own_state']['body'][need]<.2:break
            for r in [execute(w,'gather',resource,dict(mass_kg=.05)),execute(w,action,parameters=dict(mass_kg=.05),duration=duration)]:
                if r['status']!='completed':raise ValueError('Assigned native feeding rejected: '+str(r))
        else:raise ValueError('Feeding bound exceeded')


def force(path,temp,rain,ident):
    w=store.JournalWorld(path)
    parameters=dict(id=ident,observation_version=w.snapshot()['tick'],duration_s=1800,
                    temperature_c=temp,rain_mm_h=rain,cloud_fraction=.9 if rain else 0,
                    wind_x_m_s=4 if rain else 0,wind_y_m_s=0)
    return store.commit(path,dict(kind='force',parameters=parameters),ident)


def until(path,deadline):
    w=store.JournalWorld(path)
    while w.snapshot()['simulated_time_s']<deadline:
        b=w.observe_batch(['agent-1'])[0]['own_state']['body']
        if max(b['hunger'],b['thirst'])>=.27:feed(w)
        remaining=deadline-w.snapshot()['simulated_time_s']
        if remaining<=0:break
        receipt=execute(w,'rest',duration=min(10,remaining))
        if receipt['status']!='completed':raise ValueError('Assigned native rest rejected')
    return sample(path)


def sample(path):
    current=store.inspect(path);person=current['people']['agent-1']
    harmful=[e for e in person['episodes'] if e['harm']>.01 and e['intensity']>.01]
    return dict(time_s=current['snapshot']['simulated_time_s'],stress=person['stress'],mood=person['mood'],
                body=person['body'],active_harmful_episodes=len(harmful),hash=current['hash'],
                native_hash=weather.digest(weather.dumps(current['snapshot'])))


def curve(path):
    points=[]
    with closing(weather.connect(path)) as db:
        for seq,raw in db.execute('SELECT seq,result FROM mood_operations ORDER BY seq'):
            u=json.loads(raw)['updates']['agent-1']
            points.append(dict(seq=seq,tick=int(u['observation_refs'][-1].split(':')[-1]),
                               dt_s=u['appraisal']['dt_s'],before=u['stress_before'],stress=u['stress_after'],
                               mood=u['mood_after']['valence']))
    return points


def gates(arms):
    active=[arms[k] for k in ('balanced','sensitive')]
    return dict(gradual=all(0<a['cold40']['stress']<.2 and a['cold120']['stress']>.15 and
                           all(p['stress']-p['before']<=.17+1e-12 for p in a['curve'] if p['dt_s']<=10) for a in active),
                temperament=arms['sensitive']['cold120']['stress']-arms['balanced']['cold120']['stress']>=.1,
                persists=all(a['warm210']['body']['thermal']<.12 and a['warm210']['active_harmful_episodes']==0 and a['warm210']['stress']>.05 for a in active),
                recovers=all(a['warm900']['stress']<.05 and a['warm900']['stress']<.25*a['cold120']['stress'] for a in active),
                disabled=all(p['stress']==0 for p in arms['disabled']['curve']),
                physical_equal=len({a['warm900']['native_hash'] for a in arms.values()})==1,
                finite=all(0<=p['stress']<=1 and -1<=p['mood']<=1 for a in arms.values() for p in a['curve']),
                replays=all(a['replay']['verified'] for a in arms.values()),
                resumed=arms['balanced']['fresh_process_resume_matches'])


def run_seed(folder,seed):
    start=time.perf_counter();folder.mkdir(parents=True,exist_ok=False)
    source=folder/'assigned-source.sqlite'
    weather.initialize(source,seed,1,climate(),True,food_kg=8,water_kg=16)
    feed(WeatherWorld(source))
    original=hashlib.sha256(source.read_bytes()).hexdigest();arms={}
    for label,preset,mode in [('balanced','balanced','frozen'),('sensitive','sensitive','frozen'),('disabled','balanced','disabled')]:
        path=folder/(label+'.sqlite');store.attach(source,path,mode=mode,temperament=preset)
        force(path,-10,12,'actual-cold');t=sample(path)['time_s']
        cold40=until(path,t+40);cold120=until(path,t+120)
        force(path,24,0,'actual-recovery');warm_start=sample(path)['time_s']
        warm210=until(path,warm_start+210)
        copy=folder/(label+'-mid-recovery.sqlite')
        if label=='balanced':weather.save(path,copy)
        warm900=until(path,warm_start+900)
        final=store.inspect(path);s=final['snapshot'];person=final['people']['agent-1']
        actor=next(e for e in s['entities'] if e['entity_id']=='agent-1')
        if not actor['alive'] or any(s['boundary_sources_ug'].values()) or any(s['operator_sources_ug'].values()):raise ValueError('Death or undeclared material source')
        for kind in ('food','water'):
            if int(s['material_totals_ug'][kind])!=s['initial_mass_ug'][kind]:raise ValueError('Material accounting mismatch')
        arms[label]=dict(cold40=cold40,cold120=cold120,warm210=warm210,warm900=warm900,
                         curve=curve(path),replay=store.replay(path),final=final,
                         private_bytes=len(weather.dumps(person).encode()),sqlite_bytes=path.stat().st_size)
        if label=='balanced':
            r=subprocess.run([sys.executable,'-m','scripts.mood_study','resume','--folder',str(copy),'--until',str(warm_start+900),
                              '--output',str(folder/'resume-proof.json')],cwd=ROOT,capture_output=True,text=True,timeout=300)
            if r.returncode:raise ValueError('Fresh process failed: '+r.stderr)
            proof=json.loads((folder/'resume-proof.json').read_text(encoding='utf8'))
            arms[label]['fresh_process_resume_matches']=proof['hash']==final['hash']
        if time.perf_counter()-start>600:raise ValueError('Per-seed600s wall budget; partial life retained')
    result=dict(seed=seed,arms=arms,gates=gates(arms),source_preserved=hashlib.sha256(source.read_bytes()).hexdigest()==original,
                wall_s=time.perf_counter()-start)
    result['passed']=all(result['gates'].values()) and result['source_preserved']
    with gzip.open(folder/'result.json.gz','wt',encoding='utf8') as stream:json.dump(result,stream,allow_nan=False)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['development','register','confirm','resume'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/mood_f4_registration.json')
    p.add_argument('--workers',type=int,choices=[1,2],default=1);p.add_argument('--until',type=float);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    if a.command=='resume':
        until(a.folder,a.until);r=store.inspect(a.folder);proof=store.replay(a.folder)
        a.output.write_text(json.dumps(dict(hash=r['hash'],replay=proof)),encoding='utf8');return
    if a.command=='register':
        a.output.write_text(json.dumps(dict(seeds=SEEDS,files=sources(),baseline='836591d'),indent=2),encoding='utf8');return
    if a.command=='confirm':
        r=json.loads(a.registration.read_text(encoding='utf8'))
        if r['files']!=sources() or r['seeds']!=SEEDS:raise ValueError('Unsealed confirmation')
    start=time.perf_counter();rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(run_seed,a.folder/f'seed-{s}',s) for s in (SEEDS if a.command=='confirm' else [53])]
        for future in as_completed(futures):
            r=future.result();rows.append(r);print(json.dumps(dict(seed=r['seed'],passed=r['passed'],gates=r['gates'],wall_s=r['wall_s'])),flush=True)
    result=dict(files=sources(),rows=sorted(rows,key=lambda r:r['seed']),passed=all(r['passed'] for r in rows),wall_s=time.perf_counter()-start)
    with gzip.open(a.output,'wt',encoding='utf8') as stream:json.dump(result,stream,allow_nan=False)


if __name__=='__main__':main()
