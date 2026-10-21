"""Opt-in H3 contracts and bounded memory over the unchanged native H2 channel."""
from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path

from . import developmental as dev, symbols, storage
from .config import load
from .lease import Lease

DEFAULT_ACTIVE_BUDGET = 6
DEFAULT_PROTECTION_THRESHOLD = 3
ARCHIVE_BUDGET = 64


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _limits(budget, threshold):
    if type(budget) is not int or not 1 <= budget <= 16:
        raise ValueError('active budget must be an integer in 1..16')
    if type(threshold) is not int or not 1 <= threshold <= 16:
        raise ValueError('protection threshold must be an integer in 1..16')


def _contract(db, agent):
    state = symbols._contract(db, agent)
    contract = dev._read(db, 'development_records', 'community-contract-' + agent, 'id')
    if contract['module_sha256'] != module_hash():
        raise ValueError('community mechanism source mismatch; original runtime required')
    if contract['agent'] != agent or contract['run_id'] != state['run_id']:
        raise ValueError('community identity mismatch')
    if (state['active_budget'], state['protection_threshold']) != (contract['active_budget'], contract['protection_threshold']):
        raise ValueError('community budget contract mismatch')
    return state


def initialize(path, seed=41, active_budget=6, protection_threshold=3):
    """New four-person research cohort; keep H1/H2 and G defaults unchanged."""
    _limits(active_budget, protection_threshold)
    config = copy.deepcopy(load(dev.ROOT / 'config/developmental.toml'))
    config['world'].update(width_m=32., height_m=32., population=4, population_limit=4)
    dev.initialize(path, config=config, seed=seed)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent, in db.execute('SELECT agent FROM development_people').fetchall():
            state = dev._person(db, agent, agent)
            state.update(archived_comprehension={}, active_budget=active_budget,
                         protection_threshold=protection_threshold,
                         cohort_role='founder' if agent in ('agent-1', 'agent-2') else 'absent_peer',
                         community_id='a' if agent in ('agent-1', 'agent-2') else 'b',
                         symbol_control_seed=int(hashlib.sha256(f'{seed}:{agent}:symbol-control'.encode()).hexdigest()[:16], 16))
            dev._put(db, 'development_people', agent, state)
            dev._record(db, 'signal-contract-' + agent, agent, 'channel_contract', {
                'run_id': state['run_id'], 'agent': agent, 'module_sha256': symbols.module_hash(),
                'channel': {'symbols': 16, 'max_tokens': 1, 'delivery': 'native_speak'},
                'feedback': 'own visible mass change; authored demonstration scaffolding'})
            dev._record(db, 'community-contract-' + agent, agent, 'community_contract', {
                'run_id': state['run_id'], 'agent': agent, 'module_sha256': module_hash(),
                'active_budget': active_budget, 'protection_threshold': protection_threshold,
                'archive_budget': ARCHIVE_BUDGET,
                'teaching_origin': 'authored_controller; native deposit and speech only'})
        db.commit()
    return audit(path)


def recruit_newcomer(path, newcomer_id):
    """Activate an existing, never-trained cohort member once; reset no state."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _contract(db, newcomer_id)
        if state['cohort_role'] != 'absent_peer' or any(state[k] for k in
                ('production', 'comprehension', 'associations', 'objects', 'archived_comprehension')):
            raise ValueError('newcomer must be an untrained, unrecruited cohort member')
        hashes = {a: symbols.vocabulary_hash(dev._person(db, a, a))
                  for a, in db.execute('SELECT agent FROM development_people WHERE agent<>?', (newcomer_id,))}
        state['cohort_role'] = 'recruited_newcomer'
        state['version'] += 1
        ident = f'recruit-{newcomer_id}-{state["version"]}'
        dev._record(db, ident, newcomer_id, 'cohort_recruitment', {
            'run_id': state['run_id'], 'agent': newcomer_id, 'preserved_other_vocabularies': hashes,
            'newcomer_initially_empty': True, 'operation': 'activate_predeclared_native_person'})
        dev._put(db, 'development_people', newcomer_id, state)
        db.commit()
    return {'record_id': ident, 'preserved_other_vocabularies': hashes}


def partner_uncertainty(state, speaker, token, candidate_features):
    features = sorted(set(candidate_features))
    assoc = state['comprehension'].get(f'{speaker}:{token}', {})
    counts = {f: int(assoc.get(f, {}).get('n', 0)) for f in features}
    best = max(counts.values(), default=0)
    return {'counts': counts, 'total_exposures': sum(counts.values()),
            'ambiguous': best == 0 or sum(c == best for c in counts.values()) > 1,
            'origin': 'authored count-tie detector; not calibrated uncertainty'}


def enforce_memory_budget(state):
    """Finite total active budget. Overflow never exempts protected entries."""
    budget, threshold = state['active_budget'], state['protection_threshold']
    _limits(budget, threshold)
    items = [(s, f, e) for s, values in state['comprehension'].items() for f, e in values.items()]
    protected = sum(e['n'] >= threshold for _, _, e in items)
    if protected > budget:
        raise ValueError('protected memory quota reached; explicit consolidation policy required')
    items.sort(key=lambda v: (-v[2]['n'], v[0], v[1]))
    evict = items[budget:]
    archived = copy.deepcopy(state['archived_comprehension'])
    for speaker_token, feature, entry in evict:
        archived.setdefault(speaker_token, {})[feature] = dict(entry, archived_reason='finite_active_budget')
    if sum(len(v) for v in archived.values()) > ARCHIVE_BUDGET:
        raise ValueError('archived memory quota reached; preserve evidence and stop')
    state['archived_comprehension'] = archived
    for speaker_token, feature, _ in evict:
        del state['comprehension'][speaker_token][feature]
        if not state['comprehension'][speaker_token]:
            del state['comprehension'][speaker_token]
    for values in state['comprehension'].values():
        for entry in values.values():
            entry['protected'] = entry['n'] >= threshold
    return {'active': min(len(items), budget), 'protected': protected, 'evicted': len(evict),
            'archived': sum(len(v) for v in archived.values())}


def reconcile_budget(path, listener):
    """Idempotent recovery if interrupted after native grounding commits."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _contract(db, listener)
        report = enforce_memory_budget(state)
        dev._put(db, 'development_people', listener, state)
        db.commit()
    return report


def learn_attention(path, listener, speaker):
    """No feature or token injection API: use the listener's native attention proof."""
    reconcile_budget(path, listener)
    result = symbols.learn_attention(path, listener, speaker)
    result['budget'] = reconcile_budget(path, listener)
    return result


def select_reference(path, listener, speaker, candidates, after_seq=0):
    reconcile_budget(path, listener)
    observation = dev.own_observation(path, listener)
    report = symbols._heard(observation, speaker, after_seq)
    state = dev.private_state(path, listener, listener)
    features = [symbols.percept(e) for e in observation['visible_entities'] if e['entity_id'] in candidates]
    uncertainty = partner_uncertainty(state, speaker, report['text'], features) if report else {'ambiguous': True}
    decision = symbols.select_reference(path, listener, speaker, candidates, after_seq)
    decision['uncertainty'] = uncertainty
    decision['repair_requested'] = uncertainty['ambiguous']
    decision['repair_origin'] = 'authored tie detection; no invented request grammar'
    return decision


def audit(path):
    result = symbols.audit(path)
    summary = {}
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        for agent in result['people']:
            state = _contract(db, agent)
            active = sum(len(v) for v in state['comprehension'].values())
            archived = sum(len(v) for v in state['archived_comprehension'].values())
            if active > state['active_budget'] or archived > ARCHIVE_BUDGET:
                raise ValueError('unreconciled memory quota; call reconcile_budget before resuming')
            for table in ('comprehension', 'archived_comprehension'):
                for channel, entries in state[table].items():
                    for feature, entry in entries.items():
                        if not entry['evidence'] or len(entry['evidence']) != min(entry['n'], 16):
                            raise ValueError('association lacks bounded native evidence counts')
                        for ident in entry['evidence']:
                            row = db.execute('SELECT kind,payload,checksum FROM development_records WHERE id=? AND agent=?', (ident, agent)).fetchone()
                            if not row or row[0] != 'grounding' or hashlib.sha256(row[1].encode()).hexdigest() != row[2] or not json.loads(row[1])['grounded']:
                                raise ValueError('association lacks native private grounding evidence')
                            proof = json.loads(row[1])
                            if (proof['message']['speaker_id'] + ':' + proof['message']['text'] != channel
                                    or proof['observed_feature'] != feature):
                                raise ValueError('private association differs from native grounding meaning')
            summary[agent] = {'community_id': state['community_id'], 'cohort_role': state['cohort_role'],
                              'active': active, 'archived': archived, 'budget': state['active_budget']}
    result['community'] = summary
    return result
