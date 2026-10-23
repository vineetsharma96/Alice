"""Prospective native H3 replication; no dictionary-only trials or fabricated receipts."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import community, developmental as dev, symbols, storage, planning  # noqa: E402
from developmental_study import introduce, identifier, interval, SEEDS  # noqa: E402

ARMS = ['untrained_newcomer', 'newcomer_learned', 'post_interference_retained',
        'ambiguous_unrepaired', 'ambiguous_repaired']
CORE = [('food', .05), ('food', .25), ('water', .05)]


def move(path, agent, destination):
    for _ in range(96):
        observation = dev.own_observation(path, agent)
        if math.dist(observation['own_state']['position_m'], destination) < .05:
            return
        waypoint = planning._route(observation, destination)
        if not waypoint:
            raise ValueError('authored station route unavailable')
        duration = max(1, math.ceil(math.dist(observation['own_state']['position_m'], waypoint)))
        result = dev.execute(path, agent, 'move', parameters={'x_m': waypoint[0], 'y_m': waypoint[1]},
                             duration=min(duration, 60), update_memory=False)
        if result['receipt']['status'] != 'completed':
            raise ValueError('native station movement failed: ' + result['receipt']['error_code'])
    raise ValueError('bounded station route exhausted')


def tray(path, rng, far=False, definitions=None):
    positions = [[23, 24], [24, 23], [25, 24]] if far else [[1, 3], [2, 2], [3, 3]]
    rng.shuffle(positions)
    ids = []
    for (material, mass), point in zip(definitions or CORE, positions):
        ident = identifier(rng)
        introduce(path, ident, material, mass, point)
        ids.append(ident)
    return ids


def experience_summary(result):
    return {'request': result['request'], 'receipt': result['receipt'],
            'native_events': result['native_events']}


def demonstrate(path, speaker, listener, candidates, target, token=None):
    token = symbols.coin(path, speaker, target) if token is None else token
    symbols.begin_attention(path, listener, candidates)
    deposited = dev.execute(path, speaker, 'deposit', [target], {'mass_kg': .001}, update_memory=False)
    if deposited['receipt']['status'] != 'completed':
        raise ValueError('demonstration deposit failed')
    spoken = dev.execute(path, speaker, 'speak', parameters={'text': token}, update_memory=False)
    if spoken['receipt']['status'] != 'completed':
        raise ValueError('demonstration speech failed')
    feedback = community.learn_attention(path, listener, speaker)
    if not feedback['grounded']:
        raise ValueError('demonstration was not grounded in own native perception')
    return {'target_operator_only': target, 'deposit': experience_summary(deposited),
            'speech': experience_summary(spoken), 'feedback': feedback,
            'origin': 'authored_teaching_controller'}


def train(path, seed):
    community.initialize(path, seed)
    # Actual movement, never a snapshot teleport. Distant people cannot hear A.
    move(path, 'agent-4', [24, 24])
    move(path, 'agent-3', [25, 25])
    move(path, 'agent-2', [3, 3])
    rng = random.Random(seed + 300)
    for source in ('resource-1', 'resource-2'):
        result = dev.execute(path, 'agent-1', 'gather', [source], {'mass_kg': .1}, update_memory=False)
        assert result['receipt']['status'] == 'completed'
    candidates = tray(path, rng)
    sequence = list(range(3)) * 4
    rng.shuffle(sequence)
    records = []
    isolation = []
    for index in sequence:
        records.append(demonstrate(path, 'agent-1', 'agent-2', candidates, candidates[index]))
        for absent in ('agent-3', 'agent-4'):
            observation = dev.own_observation(path, absent)
            isolation.append({'agent': absent, 'observation': observation,
                              'heard_a': any(r['speaker_id'] == 'agent-1' for r in observation['audible_reports'])})
    # Separate private production by an actual far-station perceptual encounter.
    distant = tray(path, rng, far=True)
    for target in distant:
        symbols.coin(path, 'agent-4', target)
    before = community.audit(path)
    newcomer = community.recruit_newcomer(path, 'agent-3')
    # Only A's trained recipient remains at its station; the newcomer takes a
    # separate nearby position, preserving all existing bodies and memories.
    move(path, 'agent-2', [6, 6])
    move(path, 'agent-3', [3, 3])
    snapshot = storage.inspect(path)
    return {'demonstrations': records, 'isolation_observations': isolation,
            'private_exposure_isolation': not any(r['heard_a'] for r in isolation),
            'before_recruitment': before, 'recruitment': newcomer,
            'snapshot': snapshot, 'audit': community.audit(path)}


def setup_arm(path, seed, arm):
    rng = random.Random(seed + 350)
    preparation = []
    if arm == 'newcomer_learned':
        ids = tray(path, rng)
        sequence = list(range(3)) * 6
        rng.shuffle(sequence)
        for i in sequence:
            preparation.append(demonstrate(path, 'agent-1', 'agent-3', ids, ids[i]))
    elif arm == 'post_interference_retained':
        move(path, 'agent-3', [7, 7])
        move(path, 'agent-2', [3, 3])
        # Twelve different, physically perceived, single-exposure associations.
        for material in ('food', 'water'):
            for mass in (.45, .65, .85, 1.05, 1.25, 1.45):
                ids = tray(path, rng, definitions=[(material, mass)])
                preparation.append(demonstrate(path, 'agent-1', 'agent-2', ids, ids[0]))
    elif arm.startswith('ambiguous_'):
        move(path, 'agent-3', [7, 7])
        move(path, 'agent-2', [3, 3])
        move(path, 'agent-1', [6, 6])
        move(path, 'agent-4', [2, 3])
        # Real declared teacher supplies, never an inventory grant.
        for target in ('resource-1', 'resource-2'):
            result = dev.execute(path, 'agent-4', 'gather', [target], {'mass_kg': .1}, update_memory=False)
            assert result['receipt']['status'] == 'completed'
    return preparation


def evaluate(path, seed, arm):
    start = time.perf_counter()
    initial = community.audit(path)
    before = storage.inspect(path)
    preparation = setup_arm(path, seed, arm)
    scored_initial = community.audit(path)
    speaker = 'agent-4' if arm.startswith('ambiguous_') else 'agent-1'
    listener = 'agent-3' if arm in ('untrained_newcomer', 'newcomer_learned') else 'agent-2'
    rng = random.Random(seed + 400)
    sequence = list(range(3)) * 4
    rng.shuffle(sequence)
    trials = []
    for i, index in enumerate(sequence):
        if time.perf_counter() - start > 240:
            raise TimeoutError('H3 arm compute cap')
        ids = tray(path, rng)
        target = ids[index]
        candidates = list(ids)
        rng.shuffle(candidates)
        previous = dev.own_observation(path, listener)
        after_seq = max((int(r['source_event_seq']) for r in previous['audible_reports']), default=0)
        token = symbols.production_token(path, speaker, target)
        spoken = dev.execute(path, speaker, 'speak', parameters={'text': token}, update_memory=False)
        decision = community.select_reference(path, listener, speaker, candidates, after_seq)
        repair = None
        if arm == 'ambiguous_repaired' and decision['repair_requested']:
            repair = demonstrate(path, speaker, listener, candidates, target, token)
            # Remove the physical cue by scoring against new untouched objects.
            ids = tray(path, rng)
            target = ids[index]
            candidates = list(ids)
            rng.shuffle(candidates)
            previous = dev.own_observation(path, listener)
            after_seq = max((int(r['source_event_seq']) for r in previous['audible_reports']), default=0)
            spoken = dev.execute(path, speaker, 'speak', parameters={'text': token}, update_memory=False)
            decision = community.select_reference(path, listener, speaker, candidates, after_seq)
        inspected = dev.execute(path, listener, 'inspect', [decision['target']], update_memory=False)
        actual = inspected['receipt']['observable_effects'].get('description', '').split(':')[0] if inspected['receipt']['status'] == 'completed' else None
        trials.append({'trial': i, 'intended_target_operator_only': target, 'candidate_ids': candidates,
                       'emitted_token': token, 'speech': experience_summary(spoken), 'decision': decision,
                       'repair': repair, 'inspection': experience_summary(inspected),
                       'actual_target': actual, 'success': actual == target})
    final = community.audit(path)
    if arm != 'ambiguous_repaired':
        assert scored_initial['vocabulary_hashes'] == final['vocabulary_hashes']
    with closing(storage._connect(path, readonly=True)) as db:
        world, _, _, _ = storage._head(db)
        world.check_invariants()
        calls = db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
    return {'seed': seed, 'arm': arm, 'path': str(path), 'initial_head': before['state_hash'],
            'initial_audit': initial, 'scored_initial_audit': scored_initial, 'preparation': preparation,
            'trials': trials, 'successes': sum(t['success'] for t in trials),
            'rate': sum(t['success'] for t in trials) / len(trials), 'final_audit': final,
            'initial_simulated_s': before['simulated_time_s'], 'final_snapshot': storage.inspect(path),
            'wall_s': time.perf_counter() - start, 'replay': storage.replay(path),
            'native_invariants': True, 'model_calls': calls}


def seed_case(directory, seed):
    start = time.perf_counter()
    path = directory / f'{seed}-training.sqlite'
    training = train(path, seed)
    arms = []
    for arm in ARMS:
        if time.perf_counter() - start > 600:
            raise TimeoutError('H3 per-seed cap')
        branch = directory / f'{seed}-{arm}.sqlite'
        storage.save(path, 'h3-counterfactual-' + arm, branch)
        # Every complete arm resumes in a separate process.
        output = directory / f'{seed}-{arm}.json'
        child = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--evaluate', '--db', str(branch),
                                '--seed', str(seed), '--arm', arm, '--output', str(output)],
                               cwd=ROOT, capture_output=True, text=True, timeout=300)
        if child.returncode:
            raise RuntimeError(child.stderr)
        result = json.loads(output.read_text(encoding='utf-8'))
        result['fresh_process'] = True
        arms.append(result)
        print(json.dumps({'seed': seed, 'arm': arm, 'rate': result['rate'], 'wall_s': result['wall_s']}), flush=True)
    assert len({a['initial_head'] for a in arms}) == 1
    return {'seed': seed, 'training': training, 'arms': arms, 'wall_s': time.perf_counter() - start,
            'lifetimes': 'one trained world and five labelled counterfactual backups; no body reset'}


def summary(cases):
    rates = {a: sum(next(r['rate'] for r in c['arms'] if r['arm'] == a) for c in cases) / len(cases) for a in ARMS}
    improved = sum(next(r['rate'] for r in c['arms'] if r['arm'] == 'newcomer_learned') >
                   next(r['rate'] for r in c['arms'] if r['arm'] == 'untrained_newcomer') for c in cases)
    retention = True
    conventions_preserved = True
    for case in cases:
        before = case['training']['before_recruitment']['people']
        retained = next(a for a in case['arms'] if a['arm'] == 'post_interference_retained')['final_audit']
        retention &= retained['community']['agent-2']['archived'] == 9 and retained['community']['agent-2']['active'] == 6
        for channel, entries in before['agent-2']['comprehension'].items():
            for feature, entry in entries.items():
                now = retained['people']['agent-2']['comprehension'].get(channel, {}).get(feature, {})
                retention &= now.get('n') == entry['n'] and now.get('protected', False)
        for arm in case['arms']:
            for agent in ('agent-1', 'agent-4'):
                for feature, entry in before[agent]['production'].items():
                    conventions_preserved &= arm['final_audit']['people'][agent]['production'].get(feature, {}).get('token') == entry['token']
    invariants = all(c['training']['private_exposure_isolation'] and all(a['fresh_process'] and a['replay']['replay_matches']
                     and a['native_invariants'] and a['model_calls'] == 0 for a in c['arms']) for c in cases)
    gate = (rates['newcomer_learned'] >= .75 and rates['newcomer_learned'] - rates['untrained_newcomer'] >= .2
            and improved >= min(4, len(cases)) and rates['post_interference_retained'] >= .75
            and rates['ambiguous_repaired'] - rates['ambiguous_unrepaired'] >= .2 and retention and invariants and conventions_preserved)
    return {'rates': rates, 'newcomer_improved_seeds': improved, 'retention': bool(retention),
            'conventions_preserved': bool(conventions_preserved), 'invariants': invariants,
            'h3_gate': bool(gate), 'interpretation': 'Native scaffolded community reference only; authored teaching, budgets and tie repair.',
            'wilson_intervals': {a: interval(sum(next(r['successes'] for r in c['arms'] if r['arm'] == a) for c in cases), 12 * len(cases)) for a in ARMS}}


def register(path):
    files = ['underworld/community.py', 'scripts/community_study.py', 'tests/test_community.py',
             'docs/DEVELOPMENTAL_H3_NATIVE_PROTOCOL.md', 'underworld/developmental.py', 'underworld/symbols.py',
             'config/developmental.toml', 'scripts/developmental_study.py']
    path.write_text(json.dumps({'confirmation_seeds': SEEDS, 'files': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}}, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--register', type=Path)
    p.add_argument('--registration', type=Path)
    p.add_argument('--evaluate', action='store_true')
    p.add_argument('--db', type=Path)
    p.add_argument('--seed', type=int)
    p.add_argument('--arm', choices=ARMS)
    p.add_argument('--split', choices=('development', 'confirmation'))
    p.add_argument('--directory', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.register:
        register(args.register)
        return
    if not args.output:
        p.error('--output required')
    if args.evaluate:
        if not args.db or not args.arm or args.seed is None:
            p.error('evaluation requires an existing database, arm and seed')
        result = evaluate(args.db, args.seed, args.arm)
    else:
        if not args.split or not args.directory:
            p.error('new study requires split and a new directory')
        # Exact repaired H1 and native H2 evidence, no fallback to older studies.
        for registration in ('developmental_h1_registration_repaired.json', 'developmental_h2_registration.json'):
            spec = json.loads((ROOT / 'artifacts' / registration).read_text(encoding='utf-8'))
            if not all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in spec['files'].items()):
                raise ValueError('prerequisite source registration mismatch')
        if not json.loads((ROOT / 'artifacts/developmental_h1_confirmation_repaired.json').read_text(encoding='utf-8'))['summary']['h1_gate']:
            raise ValueError('H1 gate not passed')
        h2 = json.loads(gzip.decompress((ROOT / 'artifacts/developmental_h2_confirmation.json.gz').read_bytes()))
        if not h2['summary']['h2_gate']:
            raise ValueError('H2 gate not passed')
        if args.split == 'confirmation':
            if not args.registration:
                p.error('confirmation requires prospective registration')
            spec = json.loads(args.registration.read_text(encoding='utf-8'))
            if spec['confirmation_seeds'] != SEEDS or not all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha for f, sha in spec['files'].items()):
                raise ValueError('H3 prospective source mismatch')
        args.directory = args.directory.resolve()
        args.directory.mkdir(parents=True, exist_ok=False)
        start = time.perf_counter()
        cases = []
        for seed in ([41] if args.split == 'development' else SEEDS):
            if time.perf_counter() - start > 3000:
                raise TimeoutError('whole H3 study compute cap')
            cases.append(seed_case(args.directory, seed))
            args.output.write_text(json.dumps({'split': args.split, 'cases': cases}) + '\n', encoding='utf-8')
        result = {'split': args.split, 'cases': cases, 'summary': summary(cases), 'wall_s': time.perf_counter() - start}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if 'summary' in result:
        print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
