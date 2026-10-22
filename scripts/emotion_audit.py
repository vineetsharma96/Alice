"""Independently derive F1/F3 gates from actual native saves, not result labels."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import emotion_store as store,weather_store as weather
from scripts.emotion_study import HELDOUT,sources


def records(path):
    with closing(weather.connect(path)) as db:
        return [(json.loads(c),json.loads(r)) for c,r in db.execute('SELECT command,result FROM emotion_operations ORDER BY seq')]


def audit(folder,registration):
    if registration['files']!=sources() or registration['seeds']!=HELDOUT:raise ValueError('Source/seed registration mismatch')
    historical={}
    for name in ['living_world_g_registration','developmental_h1_registration_repaired','developmental_h2_registration',
                 'h3_native_registration','h4_registration','h5_registration','gap_registration','weather_registration']:
        manifest=json.loads((ROOT/f'artifacts/{name}.json').read_text(encoding='utf8'))
        pins=manifest.get('files',manifest.get('source_files'))
        if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=digest for p,digest in pins.items()):
            raise ValueError('Historical source drift: '+name)
        historical[name]=len(pins)
    rows=[];worlds={};start=time.perf_counter()
    for seed in HELDOUT:
        base=folder/f'seed-{seed}';arms={}
        for mode in ('learned','frozen','disconnected','disabled'):
            probes={}
            for probe in ('danger','harmless','reversal'):
                path=base/f'{mode}-{probe}.sqlite'
                r=next(r for c,r in reversed(records(path)) if c['kind']=='emotion-policy')
                state=store.inspect(path)
                receipt=r['native']['receipt'];agent=state['people']['agent-1']
                probes[probe]=dict(action=r['native']['choice']['action'],changed=r['influence']['changed'],
                                   expected=r['influence']['prediction']['value'],receipt=receipt['status'],
                                   protected=bool(state['climate']['exposure']['agent-1']['shelter_id']),
                                   health=1-agent['body']['injury'],alive=next(e['alive'] for e in state['snapshot']['entities'] if e['entity_id']=='agent-1'))
                if receipt['status']!='completed' or not probes[probe]['alive']:raise ValueError('Native choice failure/death')
            arms[mode]=probes
        learned=arms['learned']
        behavior=(learned['danger']['action']=='move' and learned['danger']['changed'] and learned['danger']['protected'] and
                  learned['harmless']['action']=='rest' and not learned['harmless']['changed'] and
                  learned['reversal']['action']=='rest' and not learned['reversal']['changed'] and
                  all(arms[m]['danger']['action']=='rest' and not arms[m]['danger']['changed'] for m in ('frozen','disconnected','disabled')))
        body={}
        for label in ('cold','mild'):
            path=base/f'body-{label}.sqlite'
            recovery=next(r for c,r in records(path) if c['kind']=='force' and c['parameters']['id']=='body-recovery')
            body[label]=dict(distress=-recovery['updates']['agent-1']['before']['valence'],
                             recovered=-store.inspect(path)['people']['agent-1']['affect']['valence'])
        bodily=body['cold']['distress']-body['mild']['distress']>=.1 and body['cold']['distress']-body['cold']['recovered']>=.05
        for path in sorted(base.glob('*.sqlite')):
            with closing(weather.connect(path)) as db:enrolled=db.execute("SELECT 1 FROM sqlite_master WHERE name='emotion_meta'").fetchone()
            proof=store.replay(path) if enrolled else weather.replay(path)
            worlds[str(path.resolve().relative_to(ROOT))]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),replay=proof)
        rows.append(dict(seed=seed,behavior_gate=behavior,bodily_gate=bodily,body=body,arms=arms))
        print(json.dumps(dict(seed=seed,behavior_gate=behavior,bodily_gate=bodily)),flush=True)
    if sum(r['behavior_gate'] for r in rows)<4 or not all(r['bodily_gate'] for r in rows):raise ValueError('Acceptance gate fails from actual saves')
    return dict(verified=True,registration=registration,historical=historical,rows=rows,worlds=worlds,wall_s=time.perf_counter()-start)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--registration',type=Path,default=ROOT/'artifacts/emotion_registration.json')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing audit evidence')
    result=audit(a.folder,json.loads(a.registration.read_text(encoding='utf8')))
    a.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
