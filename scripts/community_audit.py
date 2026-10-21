"""Independently check H3 native receipts, private proofs and exact study inventory."""
import argparse
from collections import Counter
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import community, developmental as dev, storage, symbols  # noqa: E402
from community_study import ARMS, SEEDS  # noqa: E402


def read(path):
    raw = path.read_bytes()
    if path.suffix == '.gz':
        raw = gzip.decompress(raw)
    return json.loads(raw)


def registered(path):
    return all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha
               for name, sha in read(path)['files'].items())


def check_experience(db, summary):
    request = summary['request']
    row = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=? AND kind=?',
                     (request['request_id'], request['agent_id'], 'experience')).fetchone()
    if not row:
        raise ValueError('missing native experience record')
    record = json.loads(row[0])
    if any(record[k] != summary[k] for k in ('request', 'receipt', 'native_events')):
        raise ValueError('report differs from durable native experience')
    if record['receipt']['status'] != 'completed':
        raise ValueError('goal lacks completed action')
    return record


def audit(study, registration):
    report = read(study)
    if report['split'] != 'confirmation' or len(report['cases']) != 5 or {c['seed'] for c in report['cases']} != set(SEEDS):
        raise ValueError('exact five-seed confirmation inventory required')
    gates = {'registered_sources': registered(registration),
             'h1_sources': registered(ROOT / 'artifacts/developmental_h1_registration_repaired.json'),
             'h2_sources': registered(ROOT / 'artifacts/developmental_h2_registration.json'),
             'g_sources': registered(ROOT / 'artifacts/living_world_g_registration.json')}
    counts = {a: [0, 0] for a in ARMS}
    durations = []
    repairs = deliveries = 0
    rejections = Counter()
    conventions = []
    for case in report['cases']:
        if len(case['arms']) != 5 or {a['arm'] for a in case['arms']} != set(ARMS):
            raise ValueError('missing or repeated arm')
        training = case['training']
        training_path = Path(case['arms'][0]['path']).parent / f'{case["seed"]}-training.sqlite'
        training_audit = community.audit(training_path)
        if not storage.replay(training_path)['replay_matches']:
            raise ValueError('training replay mismatch')
        if len(training['isolation_observations']) != 24 or any(
                any(r['speaker_id'] == 'agent-1' for r in row['observation']['audible_reports'])
                for row in training['isolation_observations']):
            raise ValueError('distant exposure isolation failed')
        before = training['before_recruitment']['people']
        for agent in ('agent-1', 'agent-2', 'agent-4'):
            if training['recruitment']['preserved_other_vocabularies'][agent] != symbols.vocabulary_hash(before[agent]):
                raise ValueError('recruitment changed existing vocabulary')
        if before['agent-3']['production'] or before['agent-3']['comprehension']:
            raise ValueError('newcomer was previously trained')
        productions = {a: {f: e['token'] for f, e in before[a]['production'].items()} for a in ('agent-1', 'agent-4')}
        conventions.append({'seed': case['seed'], 'distinct': productions['agent-1'] != productions['agent-4'], 'productions': productions})
        initial_heads = {a['initial_head'] for a in case['arms']}
        if len(initial_heads) != 1 or training['snapshot']['state_hash'] not in initial_heads:
            raise ValueError('counterfactuals lack matched initial heads')
        rates = {}
        for arm in case['arms']:
            path = Path(arm['path'])
            actual_audit = community.audit(path)
            if actual_audit != arm['final_audit'] or not storage.replay(path)['replay_matches'] or not arm['fresh_process']:
                raise ValueError('final private state or replay mismatch')
            for agent in ('agent-1', 'agent-4'):
                # Additional distractor coinage is allowed, original meanings cannot be overwritten.
                for key, token in productions[agent].items():
                    if actual_audit['people'][agent]['production'][key]['token'] != token:
                        raise ValueError('private community convention overwritten')
            if arm['arm'] != 'ambiguous_repaired' and actual_audit['vocabulary_hashes'] != arm['scored_initial_audit']['vocabulary_hashes']:
                raise ValueError('frozen arm changed vocabulary')
            if len(arm['trials']) != 12:
                raise ValueError('incomplete scored arm')
            with closing(storage._connect(path, readonly=True)) as db:
                world, _, _, _ = storage._head(db)
                world.check_invariants()
                if db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0] != 0:
                    raise ValueError('model call in model-off study')
                for trial in arm['trials']:
                    speech = check_experience(db, trial['speech'])
                    inspected = check_experience(db, trial['inspection'])
                    request = speech['request']
                    if request['target_ids'] or set(request['parameters']) != {'text'} or request['parameters']['text'] not in symbols.ALPHABET:
                        raise ValueError('message carried hidden target or gloss')
                    message = trial['decision']['message']
                    if message['source_event_seq'] not in speech['native_events']:
                        raise ValueError('delivered signal is not from the scored speech action')
                    event = dev._source_events(db, path, [message['source_event_seq']])[message['source_event_seq']]
                    if (event['type'], event['agent_id'], event['detail']) != ('speech', request['agent_id'], request['parameters']['text']):
                        raise ValueError('listener did not receive this native speech')
                    deliveries += 1
                    if inspected['request']['action_type'] != 'inspect' or inspected['request']['target_ids'] != [trial['decision']['target']]:
                        raise ValueError('reference action mismatch')
                    actual = inspected['receipt']['observable_effects']['description'].split(':')[0]
                    correct = actual == trial['intended_target_operator_only']
                    if trial['actual_target'] != actual or trial['success'] != correct:
                        raise ValueError('scored target differs from native receipt')
                    counts[arm['arm']][0] += correct
                    counts[arm['arm']][1] += 1
                    if trial['repair']:
                        repairs += 1
                        check_experience(db, trial['repair']['deposit'])
                        check_experience(db, trial['repair']['speech'])
                        if not trial['repair']['feedback']['grounded'] or trial['repair']['target_operator_only'] in trial['candidate_ids']:
                            raise ValueError('repair missing native grounding or physical cue not removed')
                for payload, in db.execute("SELECT payload FROM development_records WHERE kind='experience'"):
                    receipt = json.loads(payload)['receipt']
                    if receipt['status'] != 'completed':
                        rejections[receipt['error_code'] or receipt['status']] += 1
            if arm['arm'] == 'post_interference_retained':
                state = actual_audit['people']['agent-2']
                original = before['agent-2']['comprehension']
                for channel, entries in original.items():
                    for feature, entry in entries.items():
                        retained = state['comprehension'].get(channel, {}).get(feature)
                        if not retained or retained['n'] != entry['n'] or not retained['protected']:
                            raise ValueError('original consolidated association lost')
                if actual_audit['community']['agent-2']['active'] != 6 or actual_audit['community']['agent-2']['archived'] != 9:
                    raise ValueError('interference accounting mismatch')
                if len(arm['preparation']) != 12 or not all(p['feedback']['grounded'] for p in arm['preparation']):
                    raise ValueError('interference not native-grounded')
            successes = sum(t['success'] for t in arm['trials'])
            rates[arm['arm']] = successes / 12
            if arm['successes'] != successes or arm['rate'] != rates[arm['arm']]:
                raise ValueError('aggregate mismatch')
            durations.append({'seed': case['seed'], 'arm': arm['arm'],
                              'initial_simulated_s': arm['initial_simulated_s'],
                              'final_simulated_s': arm['final_snapshot']['simulated_time_s'],
                              'wall_s': arm['wall_s']})
        if training_audit != training['audit'] or case['wall_s'] > 600:
            raise ValueError('training state or compute cap mismatch')
    rates = {a: n / d for a, (n, d) in counts.items()}
    improved = sum(next(a['rate'] for a in c['arms'] if a['arm'] == 'newcomer_learned') >
                   next(a['rate'] for a in c['arms'] if a['arm'] == 'untrained_newcomer') for c in report['cases'])
    repair_improved = sum(next(a['rate'] for a in c['arms'] if a['arm'] == 'ambiguous_repaired') >
                          next(a['rate'] for a in c['arms'] if a['arm'] == 'ambiguous_unrepaired') for c in report['cases'])
    gates['native_receipts_persistence_isolation_budget'] = True
    gates['recomputed_metrics'] = all(abs(rates[a] - report['summary']['rates'][a]) < 1e-12 for a in ARMS)
    gates['thresholds'] = (rates['newcomer_learned'] >= .75 and rates['newcomer_learned'] - rates['untrained_newcomer'] >= .2
                          and improved >= 4 and rates['post_interference_retained'] >= .75
                          and rates['ambiguous_repaired'] - rates['ambiguous_unrepaired'] >= .2
                          and repair_improved >= 4 and repairs > 0)
    gates['compute_caps'] = report['wall_s'] <= 3000 and all(d['wall_s'] <= 240 for d in durations)
    return {'verified': all(gates.values()), 'gates': gates, 'counts': counts, 'rates': rates,
            'native_scored_deliveries': deliveries, 'authored_repairs': repairs,
            'newcomer_improved_seeds': improved, 'repair_improved_seeds': repair_improved,
            'supplementary_check': 'Also require repair improvement in at least four seeds, as in incoming algorithm-only gate.',
            'noncompleted_experiences_in_counterfactuals': dict(rejections),
            'community_conventions': conventions, 'durations': durations, 'study_wall_s': report['wall_s'],
            'claim': 'Native scaffolded H3 only; imported dictionary-only H3 experiment remains unaccepted.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True)
    p.add_argument('--registration', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.study, args.registration)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
