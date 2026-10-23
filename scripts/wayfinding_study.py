"""H4 native cooperation and separate need-scheduler evaluation."""
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
from underworld import developmental as dev, storage, symbols, wayfinding as wf  # noqa: E402
from developmental_study import introduce, identifier, interval  # noqa: E402
from community_study import demonstrate  # noqa: E402

SEEDS = [9203, 9227, 9257, 9277, 9293]
ARMS = ['enabled', 'muted', 'scrambled', 'identity']
# Operator-only station geometry; recipient policy never imports this script.
SITES = [([14, 3], [13, 3]), ([3, 14], [3, 13])]
HUB = [3, 3]


def train(path, seed):
    start = time.perf_counter()
    wf.initialize(path, seed)
    wf.walk(path, 'agent-4', [28, 28])
    wf.walk(path, 'agent-3', [29, 29])
    wf.walk(path, 'agent-2', HUB)
    rng = random.Random(seed + 600)
    words = []
    for material, point in [('food', [1, 3]), ('water', [2, 2])]:
        ident = identifier(rng)
        introduce(path, ident, material, .05, point)
        words.append(ident)
    for target in ('resource-1', 'resource-2'):
        result = dev.execute(path, 'agent-1', 'gather', [target], {'mass_kg': .01}, update_memory=False)
        assert result['receipt']['status'] == 'completed'
    identity_training = []
    for index in [0, 1, 1, 0]:
        identity_training.append(demonstrate(path, 'agent-1', 'agent-2', words, words[index]))
    relief = []
    for _ in range(2):
        for source, action in [('resource-1', 'eat'), ('resource-2', 'drink')]:
            g = dev.execute(path, 'agent-2', 'gather', [source], {'mass_kg': .05}, update_memory=False)
            c = dev.execute(path, 'agent-2', action, parameters={'mass_kg': .05},
                            duration=2 if action == 'eat' else 1, update_memory=False)
            relief.append(wf.learn_relief(path, 'agent-2', g['request']['request_id'], c['request']['request_id']))
    location_training = []
    for scout_position, listener_position in SITES:
        wf.walk(path, 'agent-1', scout_position)
        wf.walk(path, 'agent-2', listener_position)
        wf.remember_site(path, 'agent-2')
        token = wf.coin_site(path, 'agent-1')
        for _ in range(3):
            before = dev.own_observation(path, 'agent-2')
            seq = max((int(r['source_event_seq']) for r in before['audible_reports']), default=0)
            spoken = dev.execute(path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)
            learned = wf.learn_site(path, 'agent-2', 'agent-1', seq)
            location_training.append({'speech': spoken, 'learning': learned})
    wf.walk(path, 'agent-1', [2, 3])
    wf.walk(path, 'agent-2', HUB)
    for kind in ('food', 'water'):
        wf.observe_source(path, 'agent-2', kind)
    # Needs rise through actual native time, never a body-state intervention.
    for _ in range(6):
        o = dev.own_observation(path, 'agent-2')
        if o['own_state']['body']['thirst'] >= .5:
            break
        dev.execute(path, 'agent-2', 'rest', duration=30, update_memory=False)
    return {'identity_training': identity_training, 'location_training': location_training,
            'relief_training': relief, 'audit': wf.audit(path), 'snapshot': storage.inspect(path),
            'wall_s': time.perf_counter() - start, 'origin': 'authored curriculum and native co-visits'}


def prepare(path, seed, site_index, depleted=False):
    rng = random.Random(seed + 700 + site_index)
    target = identifier(rng)
    point, _ = SITES[site_index]
    introduce(path, target, 'water', .05, point)
    route = wf.walk(path, 'agent-1', point)
    sighting = wf.observe_source(path, 'agent-1')
    if not sighting or sighting['entity_id'] != target:
        raise ValueError('scout failed to observe the actual new resource')
    route += wf.walk(path, 'agent-1', [2, 3])
    depletion = None
    if depleted:
        wf.walk(path, 'agent-3', [point[0] + 1, point[1]])
        depletion = dev.execute(path, 'agent-3', 'gather', [target], {'mass_kg': .05}, update_memory=False)
        assert depletion['receipt']['status'] == 'completed'
    receiver = dev.own_observation(path, 'agent-2')
    if any(e['entity_id'] == target for e in receiver['visible_entities']):
        raise ValueError('resource is visible at the recipient hub; invalid unseen-location trial')
    return {'target_operator_only': target, 'site_index_operator_only': site_index,
            'scout_sighting': sighting, 'scout_route': route, 'depletion': depletion,
            'recipient_before_message': receiver, 'snapshot': storage.inspect(path)}


def finish(path):
    final = wf.audit(path)
    with closing(storage._connect(path, readonly=True)) as db:
        world, _, _, _ = storage._head(db)
        world.check_invariants()
        calls = db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]
        errors = []
        for payload, in db.execute("SELECT payload FROM development_records WHERE kind='experience'"):
            receipt = json.loads(payload)['receipt']
            if receipt['status'] != 'completed':
                errors.append(receipt['error_code'] or receipt['status'])
    snapshot = storage.inspect(path)
    return {'audit': final, 'snapshot': snapshot, 'replay': storage.replay(path), 'model_calls': calls,
            'native_invariants': True, 'native_rejections': errors,
            'bodies': [{'id': e['entity_id'], 'alive': e.get('alive'), 'body': e.get('body')}
                       for e in snapshot['entities'] if e['kind'] == 'actor']}


def evaluate(path, arm):
    start = time.perf_counter()
    initial = wf.audit(path)
    before = storage.inspect(path)
    observation = dev.own_observation(path, 'agent-2')
    after_seq = max((int(r['source_event_seq']) for r in observation['audible_reports']), default=0)
    spoken = wf.send(path, 'agent-1', arm)
    report = wf.receive(path, 'agent-2', 'agent-1', after_seq)
    # Explicit assigned context; this is not an autonomously chosen goal.
    execution = wf.acquire(path, 'agent-2', 'water', 'drink', report, assigned=True)
    final = finish(path)
    if initial['h4_memory_hashes'] != final['audit']['h4_memory_hashes']:
        raise ValueError('scored vocabulary or outcome predictions changed')
    if time.perf_counter() - start > 240:
        raise TimeoutError('H4 arm compute cap')
    return {'path': str(path), 'arm': arm, 'initial_head': before['state_hash'],
            'initial_simulated_s': before['simulated_time_s'], 'speech': spoken, 'report': report,
            'execution': execution, 'final': final, 'wall_s': time.perf_counter() - start,
            'initial_memory_hashes': initial['h4_memory_hashes']}


def need_window(path, frozen=False):
    initial = wf.audit(path)
    start = time.perf_counter()
    # Native displacement tests revisiting personally observed sources.
    travel = wf.walk(path, 'agent-2', [6, 6])
    steps = []
    milestones = []
    for i in range(6):
        steps.append(wf.policy_step(path, 'agent-2', frozen))
        if i in (1, 5):
            milestones.append({'decisions': i + 1, 'snapshot': storage.inspect(path)})
    final = finish(path)
    assert initial['h4_memory_hashes'] == final['audit']['h4_memory_hashes']
    return {'path': str(path), 'frozen': frozen, 'steps': steps, 'initial_audit': initial,
            'initial_travel': travel, 'milestones': milestones, 'final': final,
            'self_selected_completed': sum(bool(s['execution'] and s['execution']['goal_completed']) for s in steps),
            'wall_s': time.perf_counter() - start}


def identity_check(path, seed):
    rng = random.Random(seed + 800)
    ids = []
    for material, point in [('food', [1, 3]), ('water', [2, 2])]:
        ident = identifier(rng)
        introduce(path, ident, material, .05, point)
        ids.append(ident)
    results = []
    for target in ids:
        seq = max((int(r['source_event_seq']) for r in dev.own_observation(path, 'agent-2')['audible_reports']), default=0)
        token = symbols.production_token(path, 'agent-1', target)
        speech = dev.execute(path, 'agent-1', 'speak', parameters={'text': token}, update_memory=False)
        location_report = wf.receive(path, 'agent-2', 'agent-1', seq)
        choice = symbols.select_reference(path, 'agent-2', 'agent-1', ids, seq)
        inspected = dev.execute(path, 'agent-2', 'inspect', [choice['target']], update_memory=False)
        results.append({'target_operator_only': target, 'speech': speech, 'choice': choice,
                        'inspection': inspected, 'location_report': location_report,
                        'correct': inspected['receipt']['status'] == 'completed' and inspected['receipt']['observable_effects']['description'].split(':')[0] == target})
    return {'trials': results, 'final': finish(path)}


def child(directory, path, operation, seed, arm=None, frozen=False):
    output = directory / (path.stem + '.json')
    command = [sys.executable, str(Path(__file__).resolve()), '--evaluate', operation,
               '--db', str(path), '--seed', str(seed), '--output', str(output)]
    if arm:
        command += ['--arm', arm]
    if frozen:
        command += ['--frozen']
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stderr)
    report = json.loads(output.read_text(encoding='utf-8'))
    report['fresh_process'] = True
    return report


def seed_case(directory, seed):
    start = time.perf_counter()
    life = directory / f'{seed}-training.sqlite'
    training = train(life, seed)
    scenarios = []
    for site_index in (0, 1):
        scenario = directory / f'{seed}-site-{site_index}.sqlite'
        storage.save(life, 'scenario-' + str(site_index), scenario)
        setup = prepare(scenario, seed, site_index)
        arms = []
        for arm in ARMS:
            path = directory / f'{seed}-site-{site_index}-{arm}.sqlite'
            storage.save(scenario, arm, path)
            result = child(directory, path, 'cooperation', seed, arm)
            arms.append(result)
            print(json.dumps({'seed': seed, 'site': site_index, 'arm': arm,
                              'success': result['execution']['goal_completed'], 'wall_s': result['wall_s']}), flush=True)
        scenarios.append({'setup': setup, 'arms': arms})
    path = directory / f'{seed}-depleted.sqlite'
    storage.save(life, 'depleted', path)
    scarce_setup = prepare(path, seed, 0, depleted=True)
    scarcity = child(directory, path, 'cooperation', seed, 'enabled')
    scarcity['setup'] = scarce_setup
    needs = []
    for frozen in (False, True):
        path = directory / f'{seed}-needs-{frozen}.sqlite'
        storage.save(life, 'need-control-' + str(frozen), path)
        needs.append(child(directory, path, 'needs', seed, frozen=frozen))
    path = directory / f'{seed}-identity.sqlite'
    storage.save(life, 'identity-control', path)
    identity = child(directory, path, 'identity', seed)
    if time.perf_counter() - start > 900:
        raise TimeoutError('H4 seed compute cap')
    return {'seed': seed, 'training': training, 'scenarios': scenarios, 'scarcity': scarcity,
            'need_windows': needs, 'identity': identity, 'wall_s': time.perf_counter() - start,
            'lifetimes': 'separate matched counterfactual backups of a trained native life; no reset or replenishment'}


def summary(cases):
    counts = {arm: [sum(r['execution']['goal_completed'] for c in cases for s in c['scenarios'] for r in s['arms'] if r['arm'] == arm), 2 * len(cases)] for arm in ARMS}
    rates = {a: n / d for a, (n, d) in counts.items()}
    improved = sum(sum(r['execution']['goal_completed'] for s in c['scenarios'] for r in s['arms'] if r['arm'] == 'enabled') >
                   sum(r['execution']['goal_completed'] for s in c['scenarios'] for r in s['arms'] if r['arm'] == 'scrambled') for c in cases)
    all_trials = [r for c in cases for s in c['scenarios'] for r in s['arms']] + [c['scarcity'] for c in cases]
    invariants = all(r['fresh_process'] and r['final']['replay']['replay_matches'] and r['final']['model_calls'] == 0
                     and not r['final']['native_rejections'] for r in all_trials)
    matched = all(len({r['initial_head'] for r in s['arms']}) == 1 for c in cases for s in c['scenarios'])
    identity_separate = all(t['correct'] and t['location_report']['location'] is None for c in cases for t in c['identity']['trials'])
    scarcity = all(not c['scarcity']['execution']['goal_completed'] and not c['scarcity']['execution']['actions'] for c in cases)
    need_gate = all(c['need_windows'][0]['self_selected_completed'] >= 1 and c['need_windows'][1]['self_selected_completed'] == 0 for c in cases)
    communication = (rates['enabled'] >= .8 and all(rates['enabled'] - rates[a] >= .2 - 1e-12 for a in ('muted', 'scrambled'))
                     and improved >= min(4, len(cases)) and invariants and matched and identity_separate and scarcity)
    return {'counts': counts, 'rates': rates, 'improved_over_scrambled_seeds': improved,
            'native_invariants': invariants, 'matched_initial_heads': matched, 'identity_location_separate': identity_separate,
            'scarcity_gate': scarcity, 'communication_gate': bool(communication), 'need_policy_gate': need_gate,
            'h4_gate': bool(communication and need_gate),
            'wilson_intervals': {a: interval(n, d) for a, (n, d) in counts.items()},
            'claim': 'Bounded authored scout integration plus separately measured engineered need selection; not general independent intelligence.'}


def register(path):
    files = ['underworld/wayfinding.py', 'scripts/wayfinding_study.py', 'tests/test_wayfinding.py', 'docs/DEVELOPMENTAL_H4_PROTOCOL.md']
    path.write_text(json.dumps({'seeds': SEEDS, 'files': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}}, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--register', type=Path)
    p.add_argument('--registration', type=Path)
    p.add_argument('--split', choices=('development', 'confirmation'))
    p.add_argument('--directory', type=Path)
    p.add_argument('--evaluate', choices=('cooperation', 'needs', 'identity'))
    p.add_argument('--db', type=Path)
    p.add_argument('--seed', type=int, default=43)
    p.add_argument('--arm', choices=ARMS)
    p.add_argument('--frozen', action='store_true')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.register:
        register(args.register)
        return
    if not args.output:
        p.error('--output required')
    if args.evaluate:
        if not args.db:
            p.error('existing --db required')
        result = evaluate(args.db, args.arm) if args.evaluate == 'cooperation' else need_window(args.db, args.frozen) if args.evaluate == 'needs' else identity_check(args.db, args.seed)
    else:
        from community_audit import registered
        for n in ('developmental_h1_registration_repaired.json', 'developmental_h2_registration.json', 'h3_native_registration.json', 'living_world_g_registration.json'):
            if not registered(ROOT / 'artifacts' / n):
                raise ValueError('historical source prerequisite mismatch')
        if not json.loads((ROOT / 'artifacts/h3_native_audit.json').read_text(encoding='utf-8'))['verified']:
            raise ValueError('native H3 has not passed')
        if not args.split or not args.directory:
            p.error('study requires split and a new directory')
        if args.split == 'confirmation':
            if not args.registration:
                p.error('prospective source registration required')
            spec = json.loads(args.registration.read_text(encoding='utf-8'))
            if spec['seeds'] != SEEDS or not registered(args.registration):
                raise ValueError('frozen H4 source mismatch')
        args.directory = args.directory.resolve()
        args.directory.mkdir(parents=True, exist_ok=False)
        start = time.perf_counter()
        cases = []
        for seed in ([43] if args.split == 'development' else SEEDS):
            if time.perf_counter() - start > 4500:
                raise TimeoutError('H4 whole-study cap')
            cases.append(seed_case(args.directory, seed))
            args.output.write_text(json.dumps({'split': args.split, 'cases': cases}) + '\n', encoding='utf-8')
        result = {'split': args.split, 'cases': cases, 'summary': summary(cases), 'wall_s': time.perf_counter() - start}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if 'summary' in result:
        print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
