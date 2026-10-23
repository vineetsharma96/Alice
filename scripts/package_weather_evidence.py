"""Supplement: preserve exact weather traces and test independent-audit refusal."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.weather_audit import audit,read  # noqa: E402


def digest(raw):return hashlib.sha256(raw).hexdigest()


def negatives():
    original=read(ROOT/'artifacts/weather_confirmation.json');pins=ROOT/'artifacts/weather_registration.json'
    results={};directory=ROOT/'data/weather-confirmation-20261022'
    with tempfile.TemporaryDirectory(prefix='weather-audit-false-') as scratch:
        for name in ('false_protection','false_health','changed_registration','missing_world'):
            report=copy.deepcopy(original);registration=read(pins);root=directory
            if name=='false_protection':report['runs'][0]['reachable']['weather']['first_protection_s']['agent-1']=0
            elif name=='false_health':report['runs'][0]['reachable']['weather']['final']['climate']['exposure']['agent-1']['environmental_health_lost']=1
            elif name=='changed_registration':registration['native_build_id']='false-build'
            else:root=Path(scratch)/'absent'
            p=Path(scratch)/'report.json';q=Path(scratch)/'pins.json'
            p.write_text(json.dumps(report),encoding='utf8');q.write_text(json.dumps(registration),encoding='utf8')
            try:audit(p,root,q)
            except (ValueError,RuntimeError,OSError,sqlite3.Error) as error:results[name]=dict(refused=True,reason=str(error))
            else:raise AssertionError('Weather auditor accepted '+name)
    return results


def main():
    refused=negatives();archives=[]
    names=['weather_confirmation','weather_development','weather_development2','weather_development3',
           'weather_development4','weather_development5','weather_continuity_300','weather_continuity_600',
           'weather_continuity_1200','weather_continuity_2400','weather_w5_demo','weather_final_demo','weather_existing_control']
    for name in names:
        p=ROOT/f'artifacts/{name}.json';raw=p.read_bytes();packed=gzip.compress(raw,mtime=0)
        assert gzip.decompress(packed)==raw
        target=p.with_suffix('.json.gz')
        if target.exists():assert target.read_bytes()==packed
        else:target.write_bytes(packed)
        archives.append(dict(raw=str(p.relative_to(ROOT)).replace('\\','/'),archive=str(target.relative_to(ROOT)).replace('\\','/'),
                             raw_bytes=len(raw),archive_bytes=len(packed),raw_sha256=digest(raw),archive_sha256=digest(packed)))
    result=dict(archives=archives,negative_checks=refused,
                local_native_worlds='weather_audit.json contains 21 actual held-out save hashes; continuity and demo are separate actual local saves',
                supplemental_sources={p:digest((ROOT/p).read_bytes()) for p in ['scripts/weather_continuity_audit.py','scripts/package_weather_evidence.py','scripts/weather_existing_control.py']},
                native_saves_exported=False)
    (ROOT/'artifacts/weather_evidence_archives.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(archives=len(archives),negative_checks=refused)))


if __name__=='__main__':main()
