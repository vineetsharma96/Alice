"""Derived F4 summary from frozen raw results and independently audited saves."""
import gzip
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    raw=json.load(gzip.open(ROOT/'artifacts/mood_f4_confirmation.json.gz','rt',encoding='utf8'))
    audit=json.loads((ROOT/'artifacts/mood_f4_audit.json').read_text(encoding='utf8'))
    if not raw['passed'] or not audit['verified']:raise ValueError('Stage not verified')
    rows=[]
    for r in raw['rows']:
        arms={}
        for label,arm in r['arms'].items():
            arms[label]=dict(stress={k:arm[k]['stress'] for k in ('cold40','cold120','warm210','warm900')},
                             actual_final_simulated_s=arm['warm900']['time_s'],private_bytes=arm['private_bytes'],
                             sqlite_bytes=arm['sqlite_bytes'],updates=len(arm['curve']))
        rows.append(dict(seed=r['seed'],gates=r['gates'],wall_s=r['wall_s'],arms=arms))
    result=dict(verified=True,rows=rows,confirmation_wall_s=raw['wall_s'],audit_wall_s=audit['wall_s'],
                worlds=len(audit['worlds']),counts={k:sum(p[k] for r in audit['rows'] for p in r['arms'].values()) for k in ('accepted','completed','rejected')},
                notes=['Assigned real feeding and weather, not autonomous regulation.',
                       'Initial temperament differences are authored; no trait learning.',
                       'All forced bodily histories are identical; replication is not population generalization.',
                       'Per-seed wall times overlap with two workers; exclude extra standalone audit time.'])
    path=ROOT/'artifacts/mood_f4_summary.json'
    if path.exists():raise ValueError('Refuse replacing summary')
    path.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
