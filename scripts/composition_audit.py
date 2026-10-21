"""Recompute H5 outcomes from actual native worlds; refuse missing evidence."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import composition as comp, developmental as dev, storage  # noqa: E402
from scripts.composition_study import SEEDS, ARMS, hashes  # noqa: E402
from scripts.developmental_study import interval  # noqa: E402


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def check_experience(db, reported):
    r = reported['request']
    proof = dev._read(db, 'development_records', r['request_id'], 'id')
    if any(proof[k] != reported[k] for k in ('request', 'receipt', 'native_events')):
        raise ValueError('H5 report differs from durable native execution')
    if proof['agent'] != r['agent_id'] or proof['receipt']['status'] != 'completed':
        raise ValueError('H5 task lacks completed native action')
    return proof


def audit(study, registration):
    report, registered = read(study), read(registration)
    if report['development'] or [r['seed'] for r in report['runs']] != SEEDS:
        raise ValueError('exact H5 held-out cohort required')
    if hashes() != registered['source_files'] or hashes() != report['source_files']:
        raise ValueError('H5 frozen source mismatch')
    historical = {}
    for name in ('developmental_h1_registration_repaired', 'developmental_h2_registration',
                 'h3_native_registration', 'h4_registration', 'living_world_g_registration'):
        pins = read(ROOT / 'artifacts' / (name + '.json'))['files']
        historical[name] = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha for p, sha in pins.items())
    if not all(historical.values()):
        raise ValueError('historical registered source changed')
    totals = {a: 0 for a in ARMS}
    cases = []
    durations = []
    new_requests = {a: 0 for a in ARMS}
    model_calls = 0
    for run in report['runs']:
        if set(run['arms']) != set(ARMS):
            raise ValueError('missing H5 control arm')
        training = run['training']
        base = Path(run['arms']['learned']['path']).parent / f'{run["seed"]}-training.sqlite'
        trained = comp.audit(base)
        base_head = storage.inspect(base)['state_hash']
        if not storage.replay(base)['replay_matches']:
            raise ValueError('H5 training replay mismatch')
        with closing(storage._connect(base, readonly=True)) as db:
            training_requests = db.execute("SELECT COUNT(*) FROM development_records WHERE kind='experience'").fetchone()[0]
        seed_counts = {}
        for arm in ARMS:
            scored = run['arms'][arm]
            path = Path(scored['path'])
            final = comp.audit(path)
            if scored['native_initial_head'] != base_head or final['h5_memory_hashes'] != trained['h5_memory_hashes']:
                raise ValueError('H5 matched branch/frozen vocabulary mismatch')
            if len(scored['trials']) != 6 or not storage.replay(path)['replay_matches']:
                raise ValueError('H5 missing trials/replay failure')
            count = 0
            with closing(storage._connect(path, readonly=True)) as db:
                world, _, _, _ = storage._head(db)
                world.check_invariants()
                calls = db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
                model_calls += calls
                if calls:
                    raise ValueError('H5 unexpected model use')
                receipts = [json.loads(r[0])['receipt'] for r in db.execute("SELECT payload FROM development_records WHERE kind='experience'")]
                if any(r['status'] != 'completed' for r in receipts):
                    raise ValueError('H5 native failure requires separate investigation')
                new_requests[arm] += len(receipts) - training_requests
                for i, trial in enumerate(scored['trials']):
                    target = training['heldout'][i % 2]
                    if trial['operator_target'] != target:
                        raise ValueError('H5 held-out target inventory mismatch')
                    response = trial['response']
                    proof = dev._read(db, 'development_records', response['record_id'], 'id')
                    if dict(proof, record_id=response['record_id']) != response:
                        raise ValueError('H5 response report differs from own durable decision')
                    actual = check_experience(db, trial['inspection'])
                    if actual['request']['action_type'] != 'inspect' or actual['request']['target_ids'] != [response['target']]:
                        raise ValueError('H5 recipient did not execute its own selection')
                    expected = actual['receipt']['observable_effects'].get('description', '').split(':')[0] == target
                    if bool(trial['completed_goal']) != expected:
                        raise ValueError('H5 reported goal differs from native outcome')
                    if arm != 'muted':
                        sent = dev._read(db, 'development_records', f'h5-send-agent-1-trial-{i}-receipt', 'id')
                        speech = dev._read(db, 'development_records', sent['request_id'], 'id')
                        if speech['receipt']['status'] != 'completed' or speech['request']['requested_duration'] != len(comp.parse(sent['text'])):
                            raise ValueError('H5 channel/cost mismatch')
                        if proof['message']['text'] != sent['text']:
                            raise ValueError('H5 listener did not hear the native message')
                        values = comp.features(next(e for e in actual['before']['visible_entities'] if e['entity_id'] == target))
                        tokens = sorted(comp.parse(sent['text']))
                        if arm in ('learned', 'whole') and dev.dumps(['agent-1', tokens, values]) in trained['people']['agent-2']['h5']['messages']:
                            raise ValueError('scored H5 combination occurred in training')
                    count += expected
            if count != scored['successes']:
                raise ValueError('H5 arm count mismatch')
            snapshot = storage.inspect(path)
            if any(not e['alive'] for e in snapshot['entities'] if e['kind'] == 'actor'):
                raise ValueError('H5 death endpoint requires separate report')
            totals[arm] += count
            seed_counts[arm] = count
            durations.append(dict(seed=run['seed'], arm=arm, start_sim_s=scored['initial_sim_s'],
                                  end_sim_s=snapshot['simulated_time_s'], wall_s=scored['wall_s']))
        cases.append(dict(seed=run['seed'], successes=seed_counts, wall_s=run['wall_s']))
    n = 30
    gate = totals['learned'] >= 24 and all(totals['learned'] - totals[a] >= 6 for a in ARMS[1:]) and all(c['successes']['learned'] >= 4 for c in cases)
    if report['totals'] != totals or report['n_per_arm'] != n or report['h5_reuse_gate'] != gate:
        raise ValueError('H5 aggregate/gate mismatch')
    return dict(verified=True, h5_reuse_gate=gate, totals=totals, n_per_arm=n,
                intervals={a: interval(t, n) for a, t in totals.items()}, per_seed=cases,
                durations=durations, newly_completed_native_requests=new_requests, model_calls=model_calls,
                native_rejections=0, historical_sources_match=historical, invented_syntax=False,
                wall_s=report['wall_s'], uncertainty='30 correlated trials in five independent seed cohorts; intervals descriptive')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--registration', type=Path, default=ROOT / 'artifacts/h5_registration.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.study, args.registration)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({k: result[k] for k in ('verified', 'h5_reuse_gate', 'totals')}))


if __name__ == '__main__':
    main()
