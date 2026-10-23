"""Derive compact F5 metrics without changing raw study results."""
import argparse
import gzip
import json
from pathlib import Path
import statistics


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing summary')
    with gzip.open(a.raw,'rt',encoding='utf8') as f:r=json.load(f)
    arms={}
    for mode in ('connected','disconnected','frozen'):
        cases=[row['arms'][mode] for row in r['rows']];metrics={}
        for stage in ('relevant','unrelated','corrected'):
            probes=[c[stage] for c in cases];influence=[x['choice']['influence'] for x in probes]
            metrics[stage]=dict(changed=sum(i['changed'] for i in influence),
                completed=sum(x['choice']['native']['receipt']['status']=='completed' for x in probes),
                actual_shelter=sum(bool(x['choice']['native']['after']['own_state'].get('weather',{}).get('shelter_id')) for x in probes),
                actions=[x['choice']['native']['choice']['action'] for x in probes],
                values=[i['emotional_memory']['value'] for i in influence],
                support=[i['emotional_memory']['confidence'] for i in influence],
                mean_wall_s=statistics.mean(x['wall_s'] for x in probes),max_wall_s=max(x['wall_s'] for x in probes))
        arms[mode]=dict(probes=metrics,private_index_bytes=[c['links']['bytes'] for c in cases],
                        sqlite_bytes=[c['sqlite_bytes'] for c in cases],native_final_s=[c['final']['snapshot']['simulated_time_s'] for c in cases],
                        retained_negative=[c['links']['retained_negative'] for c in cases])
    result=dict(passed=r['passed'],gates=r['gates'],seeds=[row['seed'] for row in r['rows']],wall_s=r['wall_s'],arms=arms,
                per_seed_gates={str(row['seed']):row['gates'] for row in r['rows']},source_count=len(r['files']))
    if a.audit:
        audit=json.loads(a.audit.read_text(encoding='utf8'));main=[w for w in audit['worlds'] if Path(w['world']).stem in arms]
        result['audit']=dict(verified=audit['verified'],worlds=len(audit['worlds']),wall_s=audit['wall_s'],
                             main_accepted=sum(w['accepted'] for w in main),main_completed=sum(w['completed'] for w in main),
                             peak_index_bytes=max(w['peak_index_bytes'] for w in audit['worlds']),
                             rejections=sum(len(w['rejections']) for w in audit['worlds']),failures=sum(len(w['failures']) for w in audit['worlds']))
    a.output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
