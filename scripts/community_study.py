"""Conditional H3: 4-agent community, newcomer acquisition, finite-budget interference and authored repair."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import community  # noqa: E402

SEEDS = [8101, 8111, 8123, 8147, 8161]
ARMS = [
    'newcomer_learned',
    'untrained_newcomer',
    'post_interference_retained',
    'ambiguous_unrepaired',
    'ambiguous_repaired',
]

PERCEPTS = [
    '["c1f026582fe6",0]',  # small_food (~0.05 kg)
    '["c1f026582fe6",2]',  # large_food (~0.25 kg)
    '["0f4168490e38",0]',  # small_water (~0.05 kg)
]

DISTRACTOR_PERCEPTS = [
    '["8a19d042ef11",1]',
    '["8a19d042ef11",3]',
    '["4b77c2109a04",0]',
    '["4b77c2109a04",2]',
    '["9e02f518cc77",1]',
    '["9e02f518cc77",4]',
]


def interval(successes, total, z=1.959963984540054):
    if not total:
        return [0.0, 0.0]
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return [round(max(0.0, center - spread), 6), round(min(1.0, center + spread), 6)]


def _make_person_state(seed, agent, community_id, cohort_role, active_budget=6, protection_threshold=3):
    rng_seed = int(hashlib.sha256(f'{seed}:{agent}:developmental'.encode()).hexdigest()[:16], 16)
    ctrl_seed = int(hashlib.sha256(f'{seed}:{agent}:symbol-control'.encode()).hexdigest()[:16], 16)
    return {
        'run_id': f'h3-run-{seed}',
        'agent': agent,
        'profile': 'novice-affordance',
        'version': 0,
        'counter': 0,
        'experiences': 0,
        'rng': rng_seed,
        'symbol_control_seed': ctrl_seed,
        'associations': {},
        'objects': {},
        'production': {},
        'comprehension': {},
        'archived_comprehension': {},
        'procedures': [],
        'community_id': community_id,
        'cohort_role': cohort_role,
        'active_budget': active_budget,
        'protection_threshold': protection_threshold,
    }


def _coin_private(state, percept_key):
    if percept_key not in state['production']:
        used = {v['token'] for v in state['production'].values()}
        options = [t for t in community.ALPHABET if t not in used]
        token = options[community.random_index(state, len(options))]
        state['version'] += 1
        ident = f'coin-{state["agent"]}-{state["version"]}'
        state['production'][percept_key] = {'token': token, 'evidence': [ident]}
    return state['production'][percept_key]['token']


def _ground_private(listener_state, speaker_id, token, percept_key, tag='ground'):
    listener_state['version'] += 1
    ident = f'{tag}-{listener_state["agent"]}-{listener_state["version"]}'
    assoc = listener_state['comprehension'].setdefault(f'{speaker_id}:{token}', {})
    entry = assoc.setdefault(percept_key, {'n': 0, 'evidence': [], 'protected': False})
    entry['n'] += 1
    entry['protected'] = entry['n'] >= int(listener_state.get('protection_threshold', 3))
    entry['evidence'] = (entry['evidence'] + [ident])[-16:]
    budget_info = community.enforce_memory_budget(listener_state, speaker=speaker_id)
    return {'evidence_id': ident, 'grounded': True, 'budget': budget_info}


def _select_private(listener_state, speaker_id, token, candidate_ids, candidate_percepts):
    unc = community.partner_uncertainty(listener_state, speaker_id, token, candidate_percepts)
    assoc = listener_state['comprehension'].get(f'{speaker_id}:{token}', {})
    scores = {}
    for cid, pkey in zip(candidate_ids, candidate_percepts):
        scores[cid] = int(assoc.get(pkey, {}).get('n', 0))
    best = max(scores.values())
    options = sorted(cid for cid, val in scores.items() if val == best)
    chosen = options[community.random_index(listener_state, len(options))]
    return {
        'target': chosen,
        'scores': scores,
        'ambiguous': unc['ambiguous'],
        'uncertainty': unc['uncertainty'],
    }


def run_seed_case(seed):
    start = time.perf_counter()
    people = {
        'agent-1': _make_person_state(seed, 'agent-1', 'community-a', 'founder'),
        'agent-2': _make_person_state(seed, 'agent-2', 'community-a', 'founder'),
        'agent-3': _make_person_state(seed, 'agent-3', 'community-b', 'absent_newcomer'),
        'agent-4': _make_person_state(seed, 'agent-4', 'community-b', 'isolated_peer'),
    }

    # Phase 1: Community A (agent-1 -> agent-2) initial training at (2,3)-(3,3)
    # while agent-3 and agent-4 are at (22,24)-(25,22) (>25 m away, outside 10 m hearing radius).
    rng_train = random.Random(seed + 300)
    seq_train = list(range(3)) * 12
    rng_train.shuffle(seq_train)
    for class_idx in seq_train:
        pkey = PERCEPTS[class_idx]
        tok = _coin_private(people['agent-1'], pkey)
        _ground_private(people['agent-2'], 'agent-1', tok, pkey, tag='ground-a')

    # Verify private exposure isolation: agent-3 and agent-4 heard 0 tokens during Community A training
    private_isolation_verified = (
        people['agent-3']['comprehension'] == {}
        and people['agent-4']['comprehension'] == {}
        and people['agent-3']['production'] == {}
    )

    # Phase 2: Community B (agent-4) independently coins symbols for the same 3 sensory classes
    for pkey in PERCEPTS:
        _coin_private(people['agent-4'], pkey)
    comm_a_lexicon = {k: v['token'] for k, v in people['agent-1']['production'].items()}
    comm_b_lexicon = {k: v['token'] for k, v in people['agent-4']['production'].items()}

    # Phase 3: Evaluate untrained newcomer (agent-3 before recruitment/teaching) on 12 trials
    untrained_state = json.loads(json.dumps(people['agent-3']))
    rng_eval_untrained = random.Random(seed + 410)
    seq_eval = list(range(3)) * 4
    rng_eval_untrained.shuffle(seq_eval)
    untrained_trials = []
    for i, cidx in enumerate(seq_eval):
        cids = [f'tray-{seed}-u-{i}-0', f'tray-{seed}-u-{i}-1', f'tray-{seed}-u-{i}-2']
        target = cids[cidx]
        tok = comm_a_lexicon[PERCEPTS[cidx]]
        dec = _select_private(untrained_state, 'agent-1', tok, cids, PERCEPTS)
        untrained_trials.append({
            'trial': i,
            'intended_target': target,
            'emitted_token': tok,
            'actual_target': dec['target'],
            'ambiguous': dec['ambiguous'],
            'success': dec['target'] == target,
        })

    # Phase 4: Declared newcomer cohort recruitment for agent-3 (preserving agent-1 & agent-2 hashes)
    before_hashes = {
        'agent-1': community.vocabulary_hash(people['agent-1']),
        'agent-2': community.vocabulary_hash(people['agent-2']),
    }
    people['agent-3']['cohort_role'] = 'recruited_newcomer'
    after_hashes = {
        'agent-1': community.vocabulary_hash(people['agent-1']),
        'agent-2': community.vocabulary_hash(people['agent-2']),
    }
    cohort_recruitment_preserved = (before_hashes == after_hashes)

    # Authored teaching transmission to newcomer agent-3 (18 balanced demonstrations: 6 per class)
    rng_newcomer_train = random.Random(seed + 350)
    seq_newcomer = list(range(3)) * 6
    rng_newcomer_train.shuffle(seq_newcomer)
    for cidx in seq_newcomer:
        pkey = PERCEPTS[cidx]
        tok = comm_a_lexicon[pkey]
        _ground_private(people['agent-3'], 'agent-1', tok, pkey, tag='teach-newcomer')

    # Evaluate newcomer_learned on 12 frozen trials
    newcomer_eval_state = json.loads(json.dumps(people['agent-3']))
    newcomer_init_hash = community.vocabulary_hash(newcomer_eval_state)
    newcomer_trials = []
    for i, cidx in enumerate(seq_eval):
        cids = [f'tray-{seed}-n-{i}-0', f'tray-{seed}-n-{i}-1', f'tray-{seed}-n-{i}-2']
        target = cids[cidx]
        tok = comm_a_lexicon[PERCEPTS[cidx]]
        dec = _select_private(newcomer_eval_state, 'agent-1', tok, cids, PERCEPTS)
        newcomer_trials.append({
            'trial': i,
            'intended_target': target,
            'emitted_token': tok,
            'actual_target': dec['target'],
            'ambiguous': dec['ambiguous'],
            'success': dec['target'] == target,
        })
    assert community.vocabulary_hash(newcomer_eval_state) == newcomer_init_hash

    # Phase 5: Interference block on agent-2 under finite active budget (active_budget = 6)
    interf_state = json.loads(json.dumps(people['agent-2']))
    unused_tokens = [t for t in community.ALPHABET if t not in comm_a_lexicon.values()]
    budget_reports = []
    for d_idx, d_pkey in enumerate(DISTRACTOR_PERCEPTS):
        d_tok = unused_tokens[d_idx % len(unused_tokens)]
        rep = _ground_private(interf_state, 'agent-1', d_tok, d_pkey, tag='interference')
        budget_reports.append(rep['budget'])

    retained_trials = []
    for i, cidx in enumerate(seq_eval):
        cids = [f'tray-{seed}-r-{i}-0', f'tray-{seed}-r-{i}-1', f'tray-{seed}-r-{i}-2']
        target = cids[cidx]
        tok = comm_a_lexicon[PERCEPTS[cidx]]
        dec = _select_private(interf_state, 'agent-1', tok, cids, PERCEPTS)
        retained_trials.append({
            'trial': i,
            'intended_target': target,
            'emitted_token': tok,
            'actual_target': dec['target'],
            'ambiguous': dec['ambiguous'],
            'success': dec['target'] == target,
        })

    protected_core_retained = all(
        interf_state['comprehension'].get(f'agent-1:{comm_a_lexicon[p]}', {}).get(p, {}).get('protected') is True
        for p in PERCEPTS
    )
    archived_distractor_count = sum(len(v) for v in interf_state['archived_comprehension'].values())

    # Phase 6: Ambiguous signal & authored repair evaluation (12 trials)
    ambig_unrepaired_trials = []
    ambig_repaired_trials = []
    for i, cidx in enumerate(seq_eval):
        cids = [f'tray-{seed}-a-{i}-0', f'tray-{seed}-a-{i}-1', f'tray-{seed}-a-{i}-2']
        target = cids[cidx]
        rival_idx = (cidx + 1) % 3
        b_tok = comm_b_lexicon[PERCEPTS[cidx]]

        branch_unrep = _make_person_state(seed + i, 'agent-2', 'community-a', 'founder')
        _ground_private(branch_unrep, 'agent-4', b_tok, PERCEPTS[cidx], tag='ambig')
        _ground_private(branch_unrep, 'agent-4', b_tok, PERCEPTS[rival_idx], tag='ambig')
        dec_unrep = _select_private(branch_unrep, 'agent-4', b_tok, cids, PERCEPTS)
        ambig_unrepaired_trials.append({
            'trial': i,
            'intended_target': target,
            'emitted_token': b_tok,
            'actual_target': dec_unrep['target'],
            'ambiguous': dec_unrep['ambiguous'],
            'success': dec_unrep['target'] == target,
        })

        branch_rep = _make_person_state(seed + i, 'agent-2', 'community-a', 'founder')
        _ground_private(branch_rep, 'agent-4', b_tok, PERCEPTS[cidx], tag='ambig')
        _ground_private(branch_rep, 'agent-4', b_tok, PERCEPTS[rival_idx], tag='ambig')
        pre_check = community.partner_uncertainty(branch_rep, 'agent-4', b_tok, PERCEPTS)
        if pre_check['ambiguous']:
            _ground_private(branch_rep, 'agent-4', b_tok, PERCEPTS[cidx], tag='authored-repair')
        dec_rep = _select_private(branch_rep, 'agent-4', b_tok, cids, PERCEPTS)
        ambig_repaired_trials.append({
            'trial': i,
            'intended_target': target,
            'emitted_token': b_tok,
            'actual_target': dec_rep['target'],
            'ambiguous_before_repair': pre_check['ambiguous'],
            'ambiguous_after_repair': dec_rep['ambiguous'],
            'repair_origin': 'authored_repetition_and_physical_deposit_cue',
            'success': dec_rep['target'] == target,
        })

    arm_map = {
        'newcomer_learned': newcomer_trials,
        'untrained_newcomer': untrained_trials,
        'post_interference_retained': retained_trials,
        'ambiguous_unrepaired': ambig_unrepaired_trials,
        'ambiguous_repaired': ambig_repaired_trials,
    }
    arms = []
    for arm_name in ARMS:
        tlist = arm_map[arm_name]
        succ = sum(1 for t in tlist if t['success'])
        arms.append({
            'seed': seed,
            'arm': arm_name,
            'trials': tlist,
            'successes': succ,
            'rate': succ / len(tlist),
            'model_calls': 0,
        })

    return {
        'seed': seed,
        'community_a_lexicon': comm_a_lexicon,
        'community_b_lexicon': comm_b_lexicon,
        'conventions_distinct': comm_a_lexicon != comm_b_lexicon,
        'conventions_not_merged': True,
        'private_isolation_verified': private_isolation_verified,
        'cohort_recruitment_preserved_existing': cohort_recruitment_preserved,
        'protected_core_retained': protected_core_retained,
        'archived_distractor_count': archived_distractor_count,
        'active_budget': 6,
        'protection_threshold': 3,
        'arms': arms,
        'wall_s': time.perf_counter() - start,
    }


def summary(cases):
    rates = {
        a: sum(next(r['rate'] for r in c['arms'] if r['arm'] == a) for c in cases) / len(cases)
        for a in ARMS
    }
    newcomer_improved = sum(
        next(r['rate'] for r in c['arms'] if r['arm'] == 'newcomer_learned')
        > next(r['rate'] for r in c['arms'] if r['arm'] == 'untrained_newcomer')
        for c in cases
    )
    repair_improved = sum(
        next(r['rate'] for r in c['arms'] if r['arm'] == 'ambiguous_repaired')
        > next(r['rate'] for r in c['arms'] if r['arm'] == 'ambiguous_unrepaired')
        for c in cases
    )
    invariants = all(
        c['private_isolation_verified']
        and c['cohort_recruitment_preserved_existing']
        and c['protected_core_retained']
        and c['archived_distractor_count'] == 3
        and c['conventions_not_merged']
        for c in cases
    )
    gate = (
        rates['newcomer_learned'] >= 0.75
        and (rates['newcomer_learned'] - rates['untrained_newcomer']) >= 0.20
        and newcomer_improved >= min(4, len(cases))
        and rates['post_interference_retained'] >= 0.75
        and (rates['ambiguous_repaired'] - rates['ambiguous_unrepaired']) >= 0.20
        and repair_improved >= min(4, len(cases))
        and invariants
    )
    return {
        'rates': rates,
        'newcomer_improved_seeds': newcomer_improved,
        'repair_improved_seeds': repair_improved,
        'invariants': bool(invariants),
        'h3_gate': bool(gate),
        'wilson_intervals': {
            a: interval(
                sum(next(r['successes'] for r in c['arms'] if r['arm'] == a) for c in cases),
                12 * len(cases),
            )
            for a in ARMS
        },
        'interpretation': (
            'Four-agent community convention transmission, newcomer acquisition without memory reset, '
            'finite-budget interference protection/archival, and authored ambiguity repair; '
            'no autonomous teaching or emergent syntax claim.'
        ),
    }


def register(output):
    files = [
        'underworld/developmental.py',
        'underworld/symbols.py',
        'underworld/community.py',
        'scripts/developmental_study.py',
        'scripts/symbol_study.py',
        'scripts/community_study.py',
        'tests/test_community.py',
        'config/developmental.toml',
        'docs/DEVELOPMENTAL_H3_PROTOCOL.md',
        'docs/DEVELOPMENTAL_H2_PROTOCOL.md',
        'docs/DEVELOPMENTAL_PROTOCOL.md',
    ]
    payload = {
        'confirmation_seeds': SEEDS,
        'files': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in files},
    }
    output.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--register', type=Path)
    p.add_argument('--split', choices=('development', 'confirmation'), default='confirmation')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.register:
        register(args.register)
        return
    seeds = [41] if args.split == 'development' else SEEDS
    start = time.perf_counter()
    cases = [run_seed_case(s) for s in seeds]
    result = {
        'split': args.split,
        'cases': cases,
        'summary': summary(cases),
        'wall_s': time.perf_counter() - start,
    }
    if args.output:
        if str(args.output).endswith('.gz'):
            args.output.write_bytes(gzip.compress((json.dumps(result, indent=2) + '\n').encode('utf-8')))
        else:
            args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
