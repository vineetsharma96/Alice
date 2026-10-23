"""Supplemental finite-stock life with the emotional controller; no forcing.

Separate from registered conditioning gates. Setup is assigned roof work only.
Scheduler cursor is derived from committed policy-operation count, so resumption
does not reset its position. No body/cognitive edits, refills or episode resets.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import emotion_store as store,weather_store as weather
from underworld.weather_runtime import climate
from underworld.weather_tools import JournalWorld,roof,walk


def run(path,until,seed=53,wall_budget=600):
    start=time.perf_counter();created=False
    if not path.exists():
        source=path.with_name(path.stem+'-assigned-source.sqlite')
        weather.initialize(source,seed,4,climate(year_s=2400),False,food_kg=8,water_kg=16)
        w=JournalWorld(source)
        for i in range(2,5):walk(w,[8,3+i],f'agent-{i}')
        roof(w)
        for i,position in enumerate(([3.7,3.7],[4.3,3.7],[3.7,4.3],[4.3,4.3]),1):walk(w,position,f'agent-{i}')
        store.attach(source,path,agents=[f'agent-{i}' for i in range(1,5)])
        created=True
    initial=store.inspect(path)
    agents=sorted(initial['people'])
    inherited_cursor=initial['policies'].get('_scheduler',{}).get('cursor',0)
    while True:
        state=store.inspect(path);remaining=until-state['snapshot']['simulated_time_s']
        if remaining<=0:break
        if time.perf_counter()-start>wall_budget:raise ValueError('Explicit continuity wall budget; life retained for resume')
        if any(not e['alive'] for e in state['snapshot']['entities'] if e['kind']=='actor'):raise ValueError('Death; retained without rescue')
        with closing(weather.connect(path)) as db:
            cursor=inherited_cursor+db.execute("SELECT COUNT(*) FROM emotion_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
            serial=db.execute('SELECT COUNT(*) FROM emotion_operations').fetchone()[0]
        if remaining<5:
            command=dict(kind='step',ticks=round(remaining/.25))
        else:command=dict(kind='emotion-policy',agent=agents[cursor%len(agents)])
        store.commit(path,command,f'life-{serial}')
    final=store.inspect(path)
    with closing(weather.connect(path)) as db:
        cursor=inherited_cursor+db.execute("SELECT COUNT(*) FROM emotion_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        counts={};origins={};errors=[]
        for raw in db.execute('SELECT result FROM emotion_operations ORDER BY seq'):
            r=json.loads(raw[0]);n=r['native']
            if not isinstance(n,dict) or 'receipt' not in n:continue
            key=n['receipt']['status'];counts[key]=counts.get(key,0)+1
            origin='learned contribution + authored execution' if r['influence']['changed'] else n['choice']['origin']
            origins[origin]=origins.get(origin,0)+1
            if key!='completed':errors.append(n['receipt'])
    return dict(created=created,initial_simulated_s=initial['snapshot']['simulated_time_s'],
                final_simulated_s=final['snapshot']['simulated_time_s'],wall_s=time.perf_counter()-start,
                cursor=cursor,counts=counts,origins=origins,errors=errors,final=final,replay=store.replay(path))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--until',type=float,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    result=run(a.db,a.until)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('final','errors')}))


if __name__=='__main__':main()
