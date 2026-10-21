"""Independent delivery inventory and metric checks; no world is advanced."""
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def read(name):
    path=ROOT/name
    raw=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
    return json.loads(raw.decode('utf-8-sig'))


def source_gate(name):
    return all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in read(name)['files'].items())


def food_effect(experience):
    before=experience['before']['own_state']['inventory_ug']
    after=experience['after']['own_state']['inventory_ug']
    gain=int(after.get('food',0))-int(before.get('food',0))
    assert experience['food_gain_ug']==gain
    actual=experience['receipt']['status']=='completed' and gain>0
    assert experience['goal_success']==actual
    return actual


def model_calls(path):
    con=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)
    try:return con.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
    finally:con.close()


def main():
    seeds={8101,8111,8123,8147,8161}
    h1=read('artifacts/developmental_h1_confirmation_repaired.json')
    h2=read('artifacts/developmental_h2_confirmation.json')
    gates={
        'h1_registered_sources':source_gate('artifacts/developmental_h1_registration_repaired.json'),
        'h2_registered_sources':source_gate('artifacts/developmental_h2_registration.json'),
        'g_sources_unchanged':source_gate('artifacts/living_world_g_registration.json'),
        'h1_exact_cohort':len(h1['cells'])==20 and {(c['seed'],c['arm']) for c in h1['cells']}==
            {(s,a) for s in seeds for a in ('learning','frozen','memory','authored')},
        'h2_exact_cohort':len(h2['cases'])==5 and {c['seed'] for c in h2['cases']}==seeds and
            all(len(c['arms'])==5 and {r['arm'] for r in c['arms']}=={'learned','silence','shuffled','random','oracle'} for c in h2['cases']),
        'h1_gate':h1['summary']['h1_gate'], 'h2_gate':h2['summary']['h2_gate'],
    }
    h1_counts={a:[0,0] for a in ('learning','frozen','memory','authored')}
    for cell in h1['cells']:
        assert len(cell['training'])==15 and len(cell['evaluation'])==12
        assert cell['wall_s']<=120 and cell['replay']['replay_matches'] and cell['simulated_s']==27
        assert model_calls(cell['path'])==0
        for trial in cell['evaluation']:
            actual=food_effect(trial['experience'])
            if trial['feasible']:
                h1_counts[cell['arm']][0]+=actual;h1_counts[cell['arm']][1]+=1
    gates['h1_metrics_recomputed']=all(abs(n/d-h1['summary']['rates'][a])<1e-12 for a,(n,d) in h1_counts.items())
    h2_counts={a:[0,0] for a in ('learned','silence','shuffled','random','oracle')}
    swaps=0;native_deliveries=0;production_signatures=set()
    for case in h2['cases']:
        assert case['wall_s']<=240 and len(case['training']['trials'])==36
        assert all(t['listener_feedback']['grounded'] for t in case['training']['trials'])
        people=case['training']['audit']['people']
        assert len(people['agent-1']['production'])==3 and people['agent-1']['comprehension']=={}
        assert people['agent-2']['production']=={} and len(people['agent-2']['comprehension'])==3
        production_signatures.add(json.dumps({k:v['token'] for k,v in people['agent-1']['production'].items()},sort_keys=True))
        learned=next(r for r in case['arms'] if r['arm']=='learned')
        shuffled=next(r for r in case['arms'] if r['arm']=='shuffled')
        assert learned['fresh_process']
        for a,b in zip(learned['trials'],shuffled['trials']):
            assert a['candidate_ids']==b['candidate_ids']
            scene=lambda t:[(e['entity_id'],e['position_m'],e['kind'],e['mass_ug'])
                            for e in t['speech_or_rest']['before']['visible_entities'] if e['entity_id'] in t['candidate_ids']]
            assert scene(a)==scene(b)
            if a['emitted_token']!=b['emitted_token'] and a['actual_target']!=b['actual_target']:swaps+=1
        for arm in case['arms']:
            assert len(arm['trials'])==12 and arm['replay']['replay_matches'] and arm['native_invariants']
            assert arm['initial_vocabulary_hashes']==arm['final_vocabulary_hashes']
            assert arm['final_snapshot']['simulated_time_s']-arm['initial_simulated_s']==24
            assert model_calls(arm['path'])==0
            for trial in arm['trials']:
                inspected=trial['inspection'];receipt=inspected['receipt']
                actual=(receipt['observable_effects'].get('description','').split(':')[0]
                        if receipt['status']=='completed' else None)
                assert actual==trial['actual_target']
                correct=actual==trial['intended_target_operator_only']
                assert correct==trial['success']
                h2_counts[arm['arm']][0]+=correct;h2_counts[arm['arm']][1]+=1
                if arm['arm']!='silence':
                    message=trial['decision']['message'];spoken=trial['speech_or_rest']
                    assert message and message['observer_id']=='agent-2' and message['speaker_id']=='agent-1'
                    assert message['text']==trial['emitted_token'] and message['source_id']=='agent-1'
                    assert spoken['request']['target_ids']==[] and set(spoken['request']['parameters'])=={'text'}
                    event=spoken['native_events'][message['source_event_seq']]
                    assert event['type']=='speech' and event['detail']==message['text']
                    native_deliveries+=1
    gates['h2_metrics_recomputed']=all(abs(n/d-h2['summary']['rates'][a])<1e-12 for a,(n,d) in h2_counts.items())
    gates['native_token_swaps']=swaps==h2['summary']['causal_token_response_changes'] and swaps>0
    checks=read('artifacts/developmental_checks.json')
    gates['full_regressions']=checks['passed'] and all(c['returncode']==0 for c in checks['checks'])
    phase9=read('artifacts/developmental_phase9_audit.json')
    gates['phase9_sealed_failed']=phase9['verified_files']==3439 and phase9['recomputed_metrics_match'] and phase9['advance'] is False
    online=read('artifacts/developmental_online.json')
    gates['negative_online_diagnostic_retained']=online['missed_feasible_opportunity'] and online['replay']['replay_matches']
    assert h1['wall_s']<1800 and h2['wall_s']<1800
    report={'verification_passed':all(gates.values()),'gates':gates,'h1_counts':h1_counts,'h2_counts':h2_counts,
            'verified_native_signal_deliveries':native_deliveries,'token_response_changes':swaps,
            'distinct_seed_production_signatures':len(production_signatures),
            'h1_wall_s':h1['wall_s'],'h2_wall_s':h2['wall_s'],
            'online_adaptation_failure':online['missed_feasible_opportunity'],
            'status':{'H0':'bounded contracts/persistence verified','H1':'narrow frozen gate passed',
                      'H2':'scaffolded naming gate passed','H3':'deferred','H4':'deferred','H5':'deferred'},
            'limits':'Assigned tasks/authored sensory categories and demonstrations; no independent survival, human language, global intelligence or release-label claim.'}
    (ROOT/'artifacts/developmental_delivery_audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['verification_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
