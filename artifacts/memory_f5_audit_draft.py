"""Independent F5 index reconstruction and actual native-observation journal audit."""
import argparse
from contextlib import closing
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import memory_store as store,weather_store as weather
from underworld.weather_runtime import load


def audit(path):
    with closing(weather.connect(path)) as db:
        db.execute('BEGIN');final,_,expected_people,meta=store.head(db)
        w=load().World.restore(meta['initial'],final.snapshot()['run_id'])
        policies=json.loads(meta['policies']);people=json.loads(meta['people'])
        indexes={a:deepcopy(s['emotional_memory']) for a,s in people.items()}
        peak_bytes=0;accepted=set();completed=set();rejected={};requests={};facts={}
        for ident,raw,result in db.execute('SELECT logical_id,command,result FROM memory_operations ORDER BY seq'):
            command=json.loads(raw);expected=json.loads(result)
            before={a:w.observe_batch([a])[0] for a in people}
            if command['kind']=='emotion-policy':
                a=command['agent'];o=before[a];env=o['own_state'].get('weather',{})
                key='/'.join(('rain' if env.get('rain','none')!='none' else 'dry',
                             'chilly' if env.get('felt_temperature_c',20)<10 else 'mild','covered' if env.get('shelter_id') else 'open'))
                rows=[]
                for e in indexes[a]['entries']:
                    if e['context']==key:
                        weight=e['salience']*math.exp(-(int(o['tick'])-e['end_tick'])*e['dt_s']/180)*min(e['duration_s']/10,1)
                        if weight>1e-12:rows.append((e,weight))
                mass=sum(weight for _,weight in rows)
                value=sum(e['outcome']*weight for e,weight in rows)/mass if mass else 0.
                prediction=expected['influence']['emotional_memory']
                assert abs(prediction['value']-value)<1e-12 and abs(prediction['confidence']-(1-math.exp(-mass)))<1e-12
                assert prediction['memories']==[e['event'] for e,_ in rows]
            def emit(c):
                r=weather.apply(w,c,policies)
                if c['kind']=='submit':
                    requests[c['request']['request_id']]=c['request']['action_type']
                    if r['status']=='accepted':accepted.add(r['request_id'])
                    elif r['status']=='rejected':rejected[r['request_id']]=r.get('error_code')
                if c['kind']=='policy' and r and r.get('request'):
                    request=r['request'];requests[request['request_id']]=request['action_type']
                    if r.get('accepted'):accepted.add(request['request_id'])
                for a in people:
                    for receipt in w.observe_batch([a])[0]['recent_action_results']:
                        if receipt['request_id'] in requests and receipt['status']=='completed':completed.add(receipt['request_id'])
                return r
            actual=store.apply(w,policies,people,command,ident,emit)
            if weather.dumps(actual)!=weather.dumps(expected):raise ValueError('Stored update mismatch')
            for a,s in people.items():
                after=w.observe_batch([a])[0];u=expected['updates'][a];m=indexes[a]
                encoded=u['emotional_memory']['encoded'];dt=(int(after['tick'])-int(before[a]['tick']))*before[a]['dt_s']
                if encoded is not None:
                    old=before[a]['own_state'];new=after['own_state']
                    injury=max(0,old['body']['health']-new['body']['health'])
                    thermal=max(0,new.get('weather',{}).get('cold_burden',0)-old.get('weather',{}).get('cold_burden',0))
                    harm=min(1,max(injury/max(dt*.0015,1e-12),thermal/max(dt*.012,1e-12)))
                    relief=max(0,old['body']['hunger']-new['body']['hunger'])+max(0,old['body']['thirst']-new['body']['thirst'])
                    outcome=-harm if harm>.01 else .3 if dt>0 and new.get('weather',{}).get('cold_burden',0)<.12 and injury==0 else 0.
                    surprise=abs(outcome-u['appraisal']['prediction']['value'])/2
                    salience=min(1,.2+.4*harm+.2*min(1,relief*5)+.2*surprise)
                    env=old.get('weather',{});context='/'.join(('rain' if env.get('rain','none')!='none' else 'dry',
                           'chilly' if env.get('felt_temperature_c',20)<10 else 'mild','covered' if env.get('shelter_id') else 'open'))
                    assert encoded['event']==f'f5:{ident}:{a}' and encoded['owner']==a
                    assert encoded['start_tick']==int(before[a]['tick']) and encoded['end_tick']==int(after['tick'])
                    assert encoded['context']==context and encoded['duration_s']==dt and encoded['dt_s']==before[a]['dt_s']
                    assert abs(encoded['outcome']-outcome)<1e-12 and abs(encoded['salience']-salience)<1e-12
                    assert encoded['observation_refs']==[f"{o['run_id']}:{a}:{o['tick']}" for o in (before[a],after)]
                    if encoded['receipt_ref'] is not None:
                        assert encoded['receipt_ref'] in {r['request_id'] for r in after['recent_action_results']}
                    facts[encoded['event']]=deepcopy(encoded);m['entries'].append(encoded);m['encoded']+=1
                    selected=[];contexts=sorted({e['context'] for e in m['entries']});quota=32//len(contexts)
                    for context in contexts:
                        group=[e for e in m['entries'] if e['context']==context]
                        salient=sorted(group,key=lambda e:(e['salience'],e['end_tick'],e['event']),reverse=True)[:quota//2]
                        recent=sorted(group,key=lambda e:(e['end_tick'],e['event']),reverse=True)
                        kept={e['event']:e for e in salient+recent[:quota-quota//2]}
                        for e in recent:
                            if len(kept)>=quota:break
                            kept[e['event']]=e
                        selected.extend(kept.values())
                    m['evicted']+=len(m['entries'])-len(selected);m['entries']=sorted(selected,key=lambda e:(e['end_tick'],e['event']))
                assert m==s['emotional_memory'];assert len(m['entries'])<=32
                peak_bytes=max(peak_bytes,len(weather.dumps(m).encode()))
        assert peak_bytes<=24000
        assert people==expected_people
        for s in people.values():
            assert all(e==facts[e['event']] for e in s['emotional_memory']['entries'])
        assert w.checkpoint()==final.checkpoint()
    replay=store.replay(path)
    return dict(world=str(path.resolve().relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                verified=True,peak_index_bytes=peak_bytes,accepted=len(accepted),completed=len(completed),
                rejections=rejected,actions={k:sum(v==k for v in requests.values()) for k in sorted(set(requests.values()))},
                simulated_s=final.snapshot()['simulated_time_s'],replay=replay)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing audit')
    start=time.perf_counter();rows=[]
    for path in sorted(a.folder.glob('seed-*/*.sqlite')):
        if path.name=='assigned-source.sqlite':
            assert weather.replay(path)['replay_matches'];continue
        rows.append(audit(path));print(path.parent.name+'/'+path.name+' verified',flush=True)
        if any(path.stem.endswith('-'+label) for label in ('relevant','unrelated','corrected')):
            parent=path.with_name(path.stem.split('-')[0]+'.sqlite')
            with closing(weather.connect(path)) as child,closing(weather.connect(parent)) as main:
                query='SELECT logical_id,command,result,before_hash,after_hash FROM memory_operations ORDER BY seq'
                prefix=list(child.execute(query))[:-2]
                assert prefix==list(main.execute(query))[:len(prefix)],'Probe changed its factual prefix'
    registrations=['living_world_g_registration','developmental_h1_registration_repaired','developmental_h2_registration','h3_native_registration',
                   'h4_registration','h5_registration','gap_registration','weather_registration','emotion_registration','mood_f4_registration']
    historic={}
    for name in registrations:
        files=json.loads((ROOT/'artifacts'/f'{name}.json').read_text(encoding='utf8'))['files']
        for path,expected in files.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,(name,path)
        historic[name]=len(files)
    proof=dict(verified=bool(rows),worlds=rows,historical_registrations=historic,wall_s=time.perf_counter()-start,
               audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.output.write_text(json.dumps(proof,indent=2),encoding='utf8')


if __name__=='__main__':main()
