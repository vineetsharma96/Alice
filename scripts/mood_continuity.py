"""Continue a COPY of an existing emotional life with its inherited scheduler."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import mood_store as store,weather_store as weather


def run(path,until,source=None):
    if type(until) not in (int,float) or not math.isfinite(until) or until<0:
        raise ValueError('Absolute horizon must be finite and nonnegative')
    start=time.perf_counter();source_hash=None
    if not path.exists():
        if source is None:raise ValueError('Initial copy requires an explicit --source')
        source_hash=hashlib.sha256(source.read_bytes()).hexdigest();store.attach(source,path)
    initial=store.inspect(path);agents=sorted(initial['people'])
    dt=initial['snapshot']['dt_s']
    if abs(until-round(until/dt)*dt)>1e-9:raise ValueError('Horizon must fall on a native tick boundary')
    with closing(weather.connect(path)) as db:origin=json.loads(store.head(db)[3]['origin'])
    offset=origin['scheduler_cursor']
    while True:
        current=store.inspect(path);remaining=until-current['snapshot']['simulated_time_s']
        if remaining<=0:break
        if time.perf_counter()-start>600:raise ValueError('Wall budget reached; life retained for resume')
        if any(not e['alive'] for e in current['snapshot']['entities'] if e['kind']=='actor'):raise ValueError('Death; life retained without reset/rescue')
        with closing(weather.connect(path)) as db:
            serial=db.execute('SELECT COUNT(*) FROM mood_operations').fetchone()[0]
            cursor=offset+db.execute("SELECT COUNT(*) FROM mood_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        command=(dict(kind='step',ticks=round(remaining/current['snapshot']['dt_s'])) if remaining<5 else
                 dict(kind='emotion-policy',agent=agents[cursor%len(agents)]))
        store.commit(path,command,f'mood-life-{serial}')
    final=store.inspect(path);actions=Counter();origins=Counter();errors=[];extra_mood_choices=0
    with closing(weather.connect(path)) as db:
        cursor=offset+db.execute("SELECT COUNT(*) FROM mood_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        for raw, in db.execute('SELECT result FROM mood_operations'):
            r=json.loads(raw);n=r['native']
            if not isinstance(n,dict) or 'choice' not in n:continue
            actions[n['choice']['action']]+=1
            changed=r['influence']['changed']
            origins['personal cue + authored mood/routing' if changed else n['choice']['origin']]+=1
            if changed and r['influence']['prediction']['value']>=-.12:extra_mood_choices+=1
            if n['receipt']['status']!='completed':errors.append(n['receipt'])
    if source_hash and hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:raise ValueError('Original source life changed')
    return dict(initial_simulated_s=initial['snapshot']['simulated_time_s'],final_simulated_s=final['snapshot']['simulated_time_s'],
                source_preserved=True,source_sha256=source_hash,inherited_cursor=offset,final_cursor=cursor,
                actions=dict(actions),origins=dict(origins),additional_authored_mood_choices=extra_mood_choices,errors=errors,
                final=final,wall_s=time.perf_counter()-start,replay=store.replay(path))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--until',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    r=run(a.db,a.until,a.source);a.output.write_text(json.dumps(r,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({k:v for k,v in r.items() if k not in ('final','errors')}))


if __name__=='__main__':main()
