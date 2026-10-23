"""Prospective F5 native salience, relevance and safe correction study."""
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
from underworld import memory_store as store,emotional_memory as memory,weather_store as weather
from underworld.weather_runtime import climate
from underworld.weather_tools import JournalWorld as SetupWorld,execute,walk,roof
from scripts.emotion_study import feed

SEEDS=[19201,19207,19213,19219,19231]


def sources():
    paths=set(store.sources())|{'scripts/memory.py','scripts/memory_study.py','scripts/emotion_study.py',
                              'memory_tests/test_memory.py','memory_tests/test_viewer.py',
                              'underworld/memory_viewer.py','underworld/web/memory-panel.js',
                              'underworld/mood_viewer.py','underworld/web/mood-panel.js',
                              'scripts/mood_continuity.py',
                              'docs/MEMORY_F5_PROTOCOL.md'}
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def force(path,temp,rain,ident,setup=False):
    w=SetupWorld(path) if setup else store.JournalWorld(path)
    parameters=dict(id=ident,observation_version=w.snapshot()['tick'],duration_s=1800,
                    temperature_c=temp,rain_mm_h=rain,cloud_fraction=.9 if rain else 0,
                    wind_x_m_s=4 if rain else 0,wind_y_m_s=0)
    cmd=dict(kind='force',parameters=parameters)
    return weather.commit(path,cmd) if setup else store.commit(path,cmd,ident)


def rest(path,seconds):
    w=store.JournalWorld(path)
    for _ in range(int(seconds/10)):
        r=execute(w,'rest',duration=10)
        if r['status']!='completed':raise ValueError('Assigned native rest failed')
        if max(w.observe_batch(['agent-1'])[0]['own_state']['body'][k] for k in ('hunger','thirst'))>.55:
            feed(w);walk(w,[4,6])


def recovery(path,ident):
    force(path,24,0,ident);feed(store.JournalWorld(path));rest(path,260)
    feed(store.JournalWorld(path));walk(store.JournalWorld(path),[4,6])
    return store.inspect(path)


def probe(path,destination,temp,rain):
    weather.save(path,destination);force(destination,temp,rain,'probe-weather')
    before=store.inspect(destination);start=time.perf_counter()
    r=store.commit(destination,dict(kind='emotion-policy',agent='agent-1'),'probe-choice')
    return dict(world=str(destination.resolve().relative_to(ROOT)),before_hash=before['hash'],choice=r,wall_s=time.perf_counter()-start)


def journal(path):
    with closing(weather.connect(path)) as db:
        return list(db.execute('SELECT logical_id,command,result,before_hash,after_hash FROM memory_operations ORDER BY seq'))


def verify_links(path):
    head=store.inspect(path);s=head['people']['agent-1'];encoded={};peak=0
    for row in journal(path):
        r=json.loads(row[2])['updates']['agent-1'];e=r['emotional_memory']['encoded']
        if e:encoded[e['event']]=e
        peak=max(peak,r['emotional_memory']['retained'])
    for e in s['emotional_memory']['entries']:
        if encoded[e['event']]!=e:raise ValueError('Factual memory link changed')
    return dict(verified=True,retained=len(s['emotional_memory']['entries']),peak=peak,
                bytes=len(weather.dumps(s['emotional_memory']).encode()),encoded=len(encoded),
                retained_negative=sum(e['outcome']<0 for e in s['emotional_memory']['entries']))


def run_seed(folder,seed):
    start=time.perf_counter();folder.mkdir(parents=True,exist_ok=False)
    source=folder/'assigned-source.sqlite';weather.initialize(source,seed,1,climate(),True,food_kg=8,water_kg=16)
    force(source,24,0,'assigned-weather',True);w=SetupWorld(source);roof(w);feed(w);walk(w,[4,6])
    original=hashlib.sha256(source.read_bytes()).hexdigest();arms={}
    temperature,rain=(5+SEEDS.index(seed),8+SEEDS.index(seed)) if seed in SEEDS else (6,12)
    for mode in memory.MODES:
        path=folder/(mode+'.sqlite');store.attach(source,path,memory_mode=mode)
        force(path,-10,12,'conditioning-harm');rest(path,120)
        backup=folder/(mode+'-mid.sqlite')
        if mode=='connected':weather.save(path,backup)
        prior=recovery(path,'initial-recovery');prefix=journal(path)
        danger=probe(path,folder/(mode+'-relevant.sqlite'),temperature,rain)
        unrelated=probe(path,folder/(mode+'-unrelated.sqlite'),24,rain)
        if mode=='connected':
            output=folder/'resume.json'
            p=subprocess.run([sys.executable,'-m','scripts.memory_study','resume','--folder',str(backup),'--output',str(output)],
                             cwd=ROOT,capture_output=True,text=True,timeout=300)
            if p.returncode:raise ValueError('Fresh process failed: '+p.stderr)
            resumed=json.loads(output.read_text(encoding='utf8'))['hash']==prior['hash']
        else:resumed=None
        force(path,9.4,12,'conditioning-safe');rest(path,120)
        final=recovery(path,'safe-recovery')
        reversal=probe(path,folder/(mode+'-corrected.sqlite'),temperature,rain)
        if journal(path)[:len(prefix)]!=prefix:raise ValueError('Authoritative pre-correction history rewritten')
        snapshot=final['snapshot'];actors=[e for e in snapshot['entities'] if e['kind']=='actor']
        closed=all(int(snapshot['material_totals_ug'][k])==snapshot['initial_mass_ug'][k] for k in ('food','water'))
        no_refills=not any(snapshot['boundary_sources_ug'].values()) and not any(snapshot['operator_sources_ug'].values())
        arms[mode]=dict(prior=prior,final=final,relevant=danger,unrelated=unrelated,corrected=reversal,
                        links=verify_links(path),prefix_unchanged=True,resumed=resumed,
                        replay=store.replay(path),alive=all(e['alive'] for e in actors),accounting=closed and no_refills,
                        sqlite_bytes=path.stat().st_size)
        if time.perf_counter()-start>600:raise ValueError('600s per-seed budget; partial saves retained')
    c=arms['connected'];changed=lambda p:p['choice']['influence']['changed']
    value=lambda p:p['choice']['influence']['emotional_memory']['value']
    completed=lambda p:p['choice']['native']['receipt']['status']=='completed'
    gates=dict(relevant=changed(c['relevant']) and c['relevant']['choice']['native']['choice']['action']=='move',
               unrelated=not changed(c['unrelated']),frozen=not changed(arms['frozen']['relevant']),
               correction=not changed(c['corrected']) and value(c['corrected'])-value(c['relevant'])>=.2,
               native=all(a['alive'] and a['accounting'] and all(completed(a[k]) for k in ('relevant','unrelated','corrected')) for a in arms.values()),
               memory=all(a['links']['verified'] and a['links']['peak']<=32 and a['links']['bytes']<=24000 and a['prefix_unchanged'] for a in arms.values()),
               resume=c['resumed'],replay=all(a['replay']['verified'] for a in arms.values()),
               physical_equal=len({weather.digest(weather.dumps(a['prior']['snapshot'])) for a in arms.values()})==1 and
                              len({weather.digest(weather.dumps(a['final']['snapshot'])) for a in arms.values()})==1,
               source_preserved=hashlib.sha256(source.read_bytes()).hexdigest()==original)
    row=dict(seed=seed,arms=arms,gates=gates,passed=all(gates.values()),wall_s=time.perf_counter()-start)
    with gzip.open(folder/'result.json.gz','wt',encoding='utf8') as stream:json.dump(row,stream,allow_nan=False)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['development','register','confirm','resume'])
    p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/memory_f5_registration.json')
    p.add_argument('--workers',type=int,choices=[1,2],default=1);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    if a.command=='resume':
        r=recovery(a.folder,'initial-recovery');proof=store.replay(a.folder)
        a.output.write_text(json.dumps(dict(hash=r['hash'],replay=proof)),encoding='utf8');return
    if a.command=='register':
        a.output.write_text(json.dumps(dict(seeds=SEEDS,files=sources(),baseline='16881c2'),indent=2),encoding='utf8');return
    if a.command=='confirm':
        r=json.loads(a.registration.read_text(encoding='utf8'))
        if r['files']!=sources() or r['seeds']!=SEEDS:raise ValueError('Unsealed F5 confirmation')
    start=time.perf_counter();rows=[]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for f in as_completed([pool.submit(run_seed,a.folder/f'seed-{s}',s) for s in (SEEDS if a.command=='confirm' else [53])]):
            row=f.result();rows.append(row);print(json.dumps(dict(seed=row['seed'],gates=row['gates'],wall_s=row['wall_s'])),flush=True)
    gates={k:sum(r['gates'][k] for r in rows)>=(4 if len(rows)==5 and k in ('relevant','correction') else len(rows)) for k in rows[0]['gates']}
    result=dict(rows=sorted(rows,key=lambda r:r['seed']),files=sources(),gates=gates,passed=all(gates.values()),wall_s=time.perf_counter()-start)
    with gzip.open(a.output,'wt',encoding='utf8') as stream:json.dump(result,stream,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],wall_s=result['wall_s'])),flush=True)


if __name__=='__main__':main()
