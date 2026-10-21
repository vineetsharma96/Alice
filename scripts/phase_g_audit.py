"""Read recorded G results; separate measured integration from software gates."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))


def summarize(run):
    final=run['stages'][-1]['state'];snapshot=final['snapshot'];states=final['states']
    statuses=Counter(e['type'] for e in run['events'])
    actions={d['request'].get('request_id'):d['request'].get('action_type') for d in run['decisions']}
    completed=Counter(actions.get(e['request_id'],'unresolved_type') for e in run['events'] if e['type']=='action_completed')
    failed=[dict(e,action=actions.get(e['request_id'],'unresolved_type')) for e in run['events'] if e['type'] in ('action_failed','action_rejected')]
    goals={a:[{k:h.get(k) for k in ('goal','outcome','reason','executor_goal_credit','steps','failures','native_failures','lesson_source_id','enclosure_ids')}
              for h in s.get('tasks',{}).get('history',[])] for a,s in states.items()}
    counts={a:v['counts'] for a,v in final['knowledge'].items()}
    source_isolated=counts['agent-2']['operator_injection']==1 and all(counts[a]['operator_injection']==0 for a in ('agent-1','agent-3','agent-4'))
    pen=next((h for h in states['agent-1'].get('tasks',{}).get('history',[]) if h['goal']=='build_pen' and h['outcome']=='completed'),None)
    native={x['entity_id']:x for x in snapshot['entities']};pen_verified=False
    if pen:
        ids=pen['enclosure_ids'];pieces=[native.get(ids.get(str(i))) for i in range(1,13)]
        pen_verified=(len(ids)==13 and all(pieces) and sum(p['kind']=='fence' for p in pieces)==11
                      and sum(p['kind']=='gate' and p['radius_m']>0 for p in pieces)==1)
        assert pen_verified,'claimed pen completion must match real native pieces'
    return {'seed':run['seed'],'arm':run['arm'],'simulated_s':snapshot['simulated_time_s'],'wall_s':run['wall_s'],
            'stages':[{k:s[k] for k in ('target_simulated_s','actual_simulated_s','status','wall_s')} for s in run['stages']],
            'accepted':statuses['action_accepted'],'completed':statuses['action_completed'],'failed':statuses['action_failed'],
            'rejected':statuses['action_rejected'],'completed_action_types':dict(completed),'native_errors':failed,
            'goals':goals,'active_tasks':{a:(s.get('tasks',{}).get('active') or {}).get('goal') for a,s in states.items()},
            'pen_verified':pen_verified,'care_source_isolated':source_isolated,'knowledge_counts':counts,
            'human_survivors':sum(x['kind']=='actor' and x['alive'] for x in snapshot['entities']),
            'unmet_needs':{a:{k:v for k,v in storage_body(snapshot,a).items() if k in ('hunger','thirst','fatigue') and v>=.5} for a in states},
            'animal_survivors':sum(x['kind']=='animal' and x['alive'] for x in snapshot['entities']),
            'balances':final['balances'],'model_calls':run['model_calls'],'fallback_goals':sum(s['fallback_goals'] for s in states.values()),
            'archive_epoch':final['archive_state']['epoch'],'database_bytes':final['database_bytes'],'archive_bytes':final['archive_bytes'],
            'replay':run['replay']}


def storage_body(snapshot,agent):
    return next(x['body'] for x in snapshot['entities'] if x['entity_id']==agent)


def main():
    registration=read('artifacts/living_world_g_registration.json')
    hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==v for n,v in registration['files'].items()}
    data=read('artifacts/living_world_g_confirmation.json');runs=[summarize(r) for r in data['runs']]
    gates={'registered_sources_unchanged':all(hashes.values()),'matched_initial_physics':data['matched_initial_physics'],
           'conserved_materials':all(not any(r['balances'].values()) for r in runs),
           'source_isolation':all(r['care_source_isolated'] for r in runs),'model_off':all(r['model_calls']==0 for r in runs),
           'native_replay':all(r['replay']['replay_matches'] for r in runs)}
    report={'software_invariants_pass':all(gates.values()),'gates':gates,'registered_files':hashes,'runs':runs,
            'interpretation':'Task completion is measured, not guaranteed. Unassigned survival is not penalized for choosing no production. Finite horizons do not prove indefinite operation.'}
    (ROOT/'artifacts/living_world_g_summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'software_invariants_pass':report['software_invariants_pass'],'gates':gates,
                      'runs':[{k:r[k] for k in ('seed','arm','simulated_s','pen_verified','human_survivors','accepted','completed','failed','rejected')} for r in runs]},indent=2))


if __name__=='__main__':main()
