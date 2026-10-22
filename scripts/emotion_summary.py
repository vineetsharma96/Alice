"""Summarize retained primary evidence without replacing or rerunning experiments."""
import gzip
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1]


def main():
    raw=json.load(gzip.open(ROOT/'artifacts/emotion_confirmation.json.gz','rt',encoding='utf8'))
    rows=[]
    for row in raw['seeds']:
        arms={}
        for mode,a in row['arms'].items():
            actions={};latencies=[];completed=0;costs={}
            for probe in ('danger','harmless','reversal'):
                r=a[probe];n=r['choice']['native'];latencies.append(r['wall_s'])
                actions[probe]=n['choice']['action'];completed+=n['receipt']['status']=='completed'
                before=n['before']['own_state'];after=n['after']['own_state']
                costs[probe]=dict(simulated_s=(int(n['after']['tick'])-int(n['before']['tick']))*n['before']['dt_s'],
                                  fatigue_delta=after['body']['fatigue']-before['body']['fatigue'],
                                  food_ingested_ug=int(after['body']['food_ingested_ug'])-int(before['body']['food_ingested_ug']),
                                  water_ingested_ug=int(after['body']['water_ingested_ug'])-int(before['body']['water_ingested_ug']))
            arms[mode]=dict(actions=actions,completed=completed,rejected=3-completed,
                            learned_contributions=sum(bool(a[p]['choice']['influence']['changed']) for p in ('danger','harmless','reversal')),
                            proposal_latency_mean_s=statistics.mean(latencies),proposal_latency_max_s=max(latencies),
                            costs=costs,simulated_training_s=a['simulated_s'],sqlite_bytes=a['sqlite_bytes'],
                            private_state_bytes=a['private_state_bytes'],native_final_time_s=a['final']['snapshot']['simulated_time_s'])
        rows.append(dict(seed=row['seed'],wall_s=row['wall_s'],arms=arms,bodily=row['bodily'],
                         value_after_harm=row['arms']['learned']['danger']['choice']['influence']['prediction']['value'],
                         value_after_reversal=row['arms']['learned']['reversal']['choice']['influence']['prediction']['value']))
    summary=dict(passed=raw['passed'],wall_s=raw['wall_s'],rows=rows,notes=[
        'Completed native receipts imply accepted requests; this is not plan/JSON validity evidence.',
        '60 first-action probes; each begins from a copy of its own conditioning head.',
        'Learned safety movements cost2 simulated seconds vs baseline rest5; no matched-horizon survival advantage claimed.',
        'Native temperature/rain probe levels vary; forced conditioning yields identical fitted cue values across seeds.',
        'Assigned real feeding and roof setup are operator apparatus, not learned survival.'])
    output=ROOT/'artifacts/emotion_summary.json'
    if output.exists():raise ValueError('Refuse replacing summary')
    output.write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(dict(passed=summary['passed'],wall_s=summary['wall_s'],seeds=len(rows))))


if __name__=='__main__':main()
