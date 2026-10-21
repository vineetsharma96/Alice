"""Prospective H5 native sequence study; operator scores never enter the listener."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import composition as comp, developmental as dev, storage, wayfinding as wf  # noqa: E402
from scripts.developmental_study import introduce, identifier, interval  # noqa: E402

SEEDS = [10103, 10111, 10133, 10141, 10151]
ARMS = ['learned', 'whole', 'muted', 'first', 'second']
SOURCES = ['underworld/composition.py', 'scripts/composition_study.py',
           'tests/test_composition.py', 'docs/DEVELOPMENTAL_H5_PROTOCOL.md',
           'underworld/learning_panel.py', 'underworld/web/learning/index.html',
           'underworld/web/learning/panel.js', 'underworld/web/learning/panel.css',
           'tests/test_learning_panel.py', 'scripts/verify_learning_panel.mjs',
           'scripts/composition_audit.py', 'scripts/learner.py', 'tests/test_learner_cli.py']


def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES}


def train(path, seed):
    comp.initialize(path, seed)
    wf.walk(path, 'agent-2', [3, 3])
    rng = random.Random(seed + 800)
    definitions = [(kind, mass) for kind in ('food', 'water') for mass in (.11, .21, .31)]
    positions = [[2, 3], [3, 2], [3, 4], [4, 3], [2, 2], [4, 4]]
    rng.shuffle(positions)
    ids = [identifier(rng) for _ in definitions]
    for ident, (kind, mass), point in zip(ids, definitions, positions):
        introduce(path, ident, kind, mass, point)
    for source in ('resource-1', 'resource-2'):
        e = dev.execute(path, 'agent-1', 'gather', [source], {'mass_kg': .02}, update_memory=False)
        if e['receipt']['status'] != 'completed':
            raise ValueError('native training supply gather failed')
    schedule = [0, 1, 4, 5] * 2
    rng.shuffle(schedule)
    lessons = []
    for i, index in enumerate(schedule):
        wf.walk(path, 'agent-1', positions[index])
        text = comp.encode(path, 'agent-1', ids[index], learn=True)
        attention = f'lesson-{i}'
        comp.begin(path, 'agent-2', attention, ids)
        deposit = dev.execute(path, 'agent-1', 'deposit', [ids[index]], {'mass_kg': .001}, update_memory=False)
        if deposit['receipt']['status'] != 'completed':
            raise ValueError('native teaching deposit failed')
        speech = comp.send(path, 'agent-1', attention, text)
        learned = comp.learn(path, 'agent-2', 'agent-1', attention)
        lessons.append(dict(deposit=deposit, speech=speech, learned=learned))
    wf.walk(path, 'agent-1', [2, 3])
    return dict(ids=ids, heldout=[ids[2], ids[3]], lessons=lessons,
                snapshot=storage.inspect(path), hashes=comp.audit(path)['h5_memory_hashes'])


def evaluate(path, arm, ids, targets):
    start = time.perf_counter()
    initial = comp.audit(path)
    initial_native = storage.inspect(path)
    trials = []
    for i, target in enumerate(targets * 3):
        before = dev.own_observation(path, 'agent-2')
        seq = max((int(r['source_event_seq']) for r in before['audible_reports']), default=0)
        text = comp.encode(path, 'agent-1', target)
        if arm in ('first', 'second'):
            text = text.split()[int(arm == 'second')]
        speech = (dev.execute(path, 'agent-1', 'rest', update_memory=False) if arm == 'muted' else
                  comp.send(path, 'agent-1', f'trial-{i}', text))
        candidates = list(ids)
        random.Random(500 + i).shuffle(candidates)
        response = comp.select(path, 'agent-2', 'agent-1', candidates, seq,
                               mode=arm if arm in ('whole', 'muted') else 'learned')
        inspection = dev.execute(path, 'agent-2', 'inspect', [response['target']], update_memory=False)
        actual = inspection['receipt']['observable_effects'].get('description', '').split(':')[0]
        success = inspection['receipt']['status'] == 'completed' and actual == target
        trials.append(dict(operator_target=target, speech=speech, response=response,
                           inspection=inspection, completed_goal=success))
    final = comp.audit(path)
    if initial['h5_memory_hashes'] != final['h5_memory_hashes']:
        raise ValueError('H5 scored memory changed')
    with closing(storage._connect(path, readonly=True)) as db:
        world, _, _, _ = storage._head(db)
        world.check_invariants()
        calls = db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
        receipts = [json.loads(r[0])['receipt'] for r in db.execute("SELECT payload FROM development_records WHERE kind='experience'")]
    snapshot = storage.inspect(path)
    return dict(path=str(path), arm=arm, trials=trials, successes=sum(t['completed_goal'] for t in trials),
                native_initial_head=initial_native['state_hash'], initial_sim_s=initial_native['simulated_time_s'],
                final_sim_s=snapshot['simulated_time_s'], replay=storage.replay(path),
                memory_hashes=final['h5_memory_hashes'], model_calls=calls,
                native_rejections=[r['error_code'] or r['status'] for r in receipts if r['status'] != 'completed'],
                completed_native_requests=sum(r['status'] == 'completed' for r in receipts),
                bodies=[e for e in snapshot['entities'] if e['kind'] == 'actor'],
                random_ties=final['people']['agent-2']['h5']['random_ties'],
                protective_fallbacks=final['people']['agent-2']['h5']['protective_fallbacks'],
                wall_s=time.perf_counter() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['register', 'run', 'arm'])
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--registration', type=Path, default=ROOT / 'artifacts/h5_registration.json')
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--db', type=Path)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--ids', nargs='+')
    parser.add_argument('--targets', nargs='+')
    args = parser.parse_args()
    start = time.perf_counter()
    if args.command == 'register':
        result = dict(protocol='H5 authored factorization; not invented syntax', seeds=SEEDS,
                      development=[47], source_files=hashes(), written_utc=time.time())
    elif args.command == 'arm':
        result = evaluate(args.db, args.arm, args.ids, args.targets)
    else:
        if not args.development:
            registration = json.loads(args.registration.read_text(encoding='utf8'))
            if registration['source_files'] != hashes() or registration['seeds'] != SEEDS:
                raise ValueError('H5 frozen registration mismatch')
        args.directory.mkdir(parents=True, exist_ok=False)
        runs = []
        for seed in ([47] if args.development else SEEDS):
            seed_start = time.perf_counter()
            base = args.directory / f'{seed}-training.sqlite'
            trained = train(base, seed)
            arms = {}
            for arm in ARMS:
                path = args.directory / f'{seed}-{arm}.sqlite'
                storage.save(base, f'h5-{arm}', path)
                output = args.directory / f'{seed}-{arm}.json'
                subprocess.run([sys.executable, __file__, 'arm', '--db', str(path), '--arm', arm,
                    '--ids', *trained['ids'], '--targets', *trained['heldout'], '--output', str(output)],
                    check=True, timeout=120)
                arms[arm] = json.loads(output.read_text(encoding='utf8'))
            elapsed = time.perf_counter() - seed_start
            if elapsed > 300 or time.perf_counter() - start > 1800:
                raise TimeoutError('H5 study compute cap')
            runs.append(dict(seed=seed, training=trained, arms=arms, wall_s=elapsed))
        n = len(runs) * 6
        totals = {a: sum(r['arms'][a]['successes'] for r in runs) for a in ARMS}
        gate = (totals['learned'] / n >= .8 and all((totals['learned'] - totals[a]) / n >= .2 - 1e-9 for a in ARMS[1:])
                and all(r['arms']['learned']['successes'] >= 4 for r in runs))
        result = dict(development=args.development, source_files=hashes(), runs=runs,
                      totals=totals, n_per_arm=n, intervals={a: interval(t, n) for a, t in totals.items()},
                      h5_reuse_gate=gate, invented_syntax=False, wall_s=time.perf_counter() - start)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError('refuse overwriting H5 evidence')
    args.output.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k in ('totals', 'h5_reuse_gate', 'wall_s', 'source_files')}))


if __name__ == '__main__':
    main()
