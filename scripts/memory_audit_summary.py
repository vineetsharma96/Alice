"""Reconcile independent save audits, the frozen source seal and actual F5 gates."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.memory_study import SEEDS,sources
from underworld import memory_store as store,weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing audit summary')
    seal=json.loads((ROOT/'artifacts/memory_f5_registration.json').read_text(encoding='utf8'))
    with gzip.open(ROOT/'artifacts/memory_f5_confirmation.json.gz','rt',encoding='utf8') as f:raw=json.load(f)
    assert seal['files']==sources()==raw['files'] and seal['seeds']==SEEDS
    assert [r['seed'] for r in raw['rows']]==SEEDS
    audits=[json.loads((ROOT/f'artifacts/memory_f5_audit_{seed}.json').read_text(encoding='utf8')) for seed in SEEDS]
    worlds=[w for proof in audits for w in proof['worlds']];initial=[w for proof in audits for w in proof['source_worlds']]
    assert len(worlds)==65 and len(initial)==5 and all(proof['verified'] for proof in audits)
    for w in worlds+initial:assert hashlib.sha256((ROOT/w['world']).read_bytes()).hexdigest()==w['sha256']
    rows=[]
    for row in raw['rows']:
        folder=a.folder/f"seed-{row['seed']}";arms={};heads=[];prior_native=[]
        for mode in ('connected','disconnected','frozen'):
            path=folder/(mode+'.sqlite');actual=store.inspect(path);case=row['arms'][mode]
            # Native vectors are tuples; saved wire vectors are JSON arrays.
            assert weather.dumps(actual)==weather.dumps(case['final']);heads.append(weather.dumps(actual['snapshot']))
            assert all(e['alive'] for e in actual['snapshot']['entities'] if e['kind']=='actor')
            assert all(int(actual['snapshot']['material_totals_ug'][k])==actual['snapshot']['initial_mass_ug'][k] for k in ('food','water'))
            assert not any(actual['snapshot']['boundary_sources_ug'].values()) and not any(actual['snapshot']['operator_sources_ug'].values())
            with closing(weather.connect(path)) as db:
                prior_hash=db.execute("SELECT before_hash FROM memory_operations WHERE logical_id='conditioning-safe'").fetchone()[0]
                assert prior_hash==case['prior']['hash']
                boundary=db.execute("SELECT seq FROM weather_operations WHERE json_extract(command,'$.kind')='force' AND json_extract(command,'$.parameters.id')='conditioning-safe'").fetchone()[0]
                prefix=list(db.execute('SELECT command,before_hash,after_hash,result FROM weather_operations WHERE seq<? ORDER BY seq',(boundary,)))
            prior_native.append(weather.dumps(prefix));probes={}
            for stage,suffix in [('relevant','relevant'),('unrelated','unrelated'),('corrected','corrected')]:
                with closing(weather.connect(folder/f'{mode}-{suffix}.sqlite')) as db:
                    result,before=db.execute("SELECT result,before_hash FROM memory_operations WHERE logical_id='probe-choice'").fetchone()
                r=json.loads(result);assert r==case[stage]['choice'] and before==case[stage]['before_hash']
                assert r['native']['receipt']['status']=='completed';probes[stage]=r
            arms[mode]=probes
        c=arms['connected'];changed=lambda r:r['influence']['changed'];value=lambda r:r['influence']['emotional_memory']['value']
        gates=dict(relevant=changed(c['relevant']) and c['relevant']['native']['choice']['action']=='move',
                   unrelated=not changed(c['unrelated']),frozen=not changed(arms['frozen']['relevant']),
                   correction=not changed(c['corrected']) and value(c['corrected'])-value(c['relevant'])>=.2,
                   physical_equal=len(set(heads))==1 and len(set(prior_native))==1,
                   resume=store.inspect(folder/'connected-mid.sqlite')['hash']==row['arms']['connected']['prior']['hash'])
        assert all(gates.values());rows.append(dict(seed=row['seed'],gates=gates))
    result=dict(verified=True,worlds=worlds,source_worlds=initial,rows=rows,historical_registrations=audits[0]['historical_registrations'],
                wall_s=sum(proof['wall_s'] for proof in audits),note='Sum of independent audit windows; some overlap. Excludes this reconciliation and the retained failed audit attempt.',
                audit_source_sha256=audits[0]['audit_source_sha256'],summary_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    assert all(proof['audit_source_sha256']==result['audit_source_sha256'] for proof in audits)
    a.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
