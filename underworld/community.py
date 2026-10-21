"""Stage H3: four-agent community, newcomer recruitment, finite-budget forgetting and authored repair."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path

from .lease import Lease
from .wire import dumps

ALPHABET = tuple(f's{i:02x}' for i in range(16))
DEFAULT_ACTIVE_BUDGET = 6
DEFAULT_PROTECTION_THRESHOLD = 3


def _lazy_deps():
    from . import developmental as dev, symbols, storage
    return dev, symbols, storage


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(dumps(value).encode('utf-8')).hexdigest()


def vocabulary_hash(state):
    return digest({k: state[k] for k in ('production', 'comprehension')})


def random_index(state, count):
    if count <= 0:
        raise ValueError('empty choice set')
    x = (int(state['rng']) + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
    state['rng'] = x
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & ((1 << 64) - 1)
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & ((1 << 64) - 1)
    return ((x ^ (x >> 31)) & ((1 << 64) - 1)) % count


def _community_contract(db, agent):
    dev, symbols, _ = _lazy_deps()
    state = symbols._contract(db, agent)
    ident = 'community-contract-' + agent
    row = db.execute('SELECT payload,checksum FROM development_records WHERE id=? AND agent=?',
                     (ident, agent)).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
        raise ValueError('missing private H3 community contract')
    contract = json.loads(row[0])
    if contract['module_sha256'] != module_hash():
        raise ValueError('community mechanism source mismatch; original runtime required')
    return state, contract


def initialize(path, seed=41, population=4, active_budget=DEFAULT_ACTIVE_BUDGET,
               protection_threshold=DEFAULT_PROTECTION_THRESHOLD):
    """Initialize a 4-agent world (32x32 m, 4 agents, 6 animals) with H3 community contracts."""
    dev, symbols, storage = _lazy_deps()
    symbols.initialize(path, seed=seed, population=population)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent, in db.execute('SELECT agent FROM development_people').fetchall():
            state = dev._person(db, agent, agent)
            state.setdefault('archived_comprehension', {})
            state.setdefault('exposure_history', [])
            state.setdefault('community_id', 'community-a' if agent in ('agent-1', 'agent-2') else 'community-b')
            state.setdefault('cohort_role', 'founder' if agent in ('agent-1', 'agent-2') else 'isolated_peer')
            state['active_budget'] = int(active_budget)
            state['protection_threshold'] = int(protection_threshold)
            dev._put(db, 'development_people', agent, state)
            dev._record(db, 'community-contract-' + agent, agent, 'community_contract', {
                'run_id': state['run_id'],
                'agent': agent,
                'module_sha256': module_hash(),
                'community_id': state['community_id'],
                'cohort_role': state['cohort_role'],
                'active_budget': int(active_budget),
                'protection_threshold': int(protection_threshold),
                'repair_affordance': 'authored_repetition_and_physical_deposit_cue',
                'teaching_mode': 'authored_teaching_controller',
            })
        db.commit()
    return audit(path)


def recruit_newcomer(path, newcomer_id, preserved_agents=('agent-1', 'agent-2'),
                     active_budget=DEFAULT_ACTIVE_BUDGET,
                     protection_threshold=DEFAULT_PROTECTION_THRESHOLD):
    """Declared cohort operation: register/verify a newcomer with empty associations without resetting existing people."""
    dev, symbols, storage = _lazy_deps()
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        before_hashes = {}
        for existing in preserved_agents:
            s = dev._person(db, existing, existing)
            before_hashes[existing] = symbols.vocabulary_hash(s)
        state = dev._person(db, newcomer_id, newcomer_id)
        if state['production'] or state['comprehension'] or state['associations']:
            raise ValueError('newcomer already has populated associations; refusing silent memory reset')
        state['cohort_role'] = 'recruited_newcomer'
        state['archived_comprehension'] = {}
        state['exposure_history'] = []
        state['active_budget'] = int(active_budget)
        state['protection_threshold'] = int(protection_threshold)
        state['version'] += 1
        ident = f'recruit-{newcomer_id}-{state["version"]}'
        dev._record(db, ident, newcomer_id, 'cohort_recruitment', {
            'run_id': state['run_id'],
            'agent': newcomer_id,
            'cohort_operation': 'recruit_newcomer',
            'initial_production_empty': state['production'] == {},
            'initial_comprehension_empty': state['comprehension'] == {},
            'preserved_existing_hashes': before_hashes,
        })
        dev._put(db, 'development_people', newcomer_id, state)
        for existing in preserved_agents:
            after_s = dev._person(db, existing, existing)
            if symbols.vocabulary_hash(after_s) != before_hashes[existing]:
                raise ValueError('existing inhabitant vocabulary modified during newcomer recruitment')
        db.commit()
        return {
            'newcomer': newcomer_id,
            'recruitment_record': ident,
            'preserved_existing_hashes': before_hashes,
            'newcomer_vocabulary_hash': symbols.vocabulary_hash(state),
        }


def partner_uncertainty(state, speaker, token, candidate_features):
    """Compute partner-specific entropy/margin and ambiguity over visible candidate features."""
    assoc = state['comprehension'].get(f'{speaker}:{token}', {})
    counts = [int(assoc.get(f, {}).get('n', 0)) for f in candidate_features]
    total = sum(counts)
    best = max(counts, default=0)
    top_ties = sum(1 for c in counts if c == best)
    ambiguous = (total == 0) or (top_ties > 1)
    uncertainty = round(1.0 / (total + max(1, len(candidate_features))), 4)
    return {
        'speaker_token': f'{speaker}:{token}',
        'counts': dict(zip(candidate_features, counts)),
        'total_exposures': total,
        'best_count': best,
        'top_ties': top_ties,
        'ambiguous': ambiguous,
        'uncertainty': uncertainty,
    }


def enforce_memory_budget(state, speaker=None):
    """Enforce finite active association budget while protecting consolidated (n >= threshold) entries."""
    budget = int(state.get('active_budget', DEFAULT_ACTIVE_BUDGET))
    threshold = int(state.get('protection_threshold', DEFAULT_PROTECTION_THRESHOLD))
    archived = state.setdefault('archived_comprehension', {})

    items = []
    for st_key, fmap in list(state['comprehension'].items()):
        if speaker and not st_key.startswith(speaker + ':'):
            continue
        for f_key, entry in list(fmap.items()):
            protected = int(entry.get('n', 0)) >= threshold
            entry['protected'] = protected
            last_ev = entry.get('evidence', [''])[-1]
            items.append((st_key, f_key, int(entry.get('n', 0)), protected, last_ev, entry))

    if len(items) <= budget:
        return {
            'active_count': len(items),
            'protected_count': sum(1 for it in items if it[3]),
            'evicted_to_archive': 0,
        }

    items.sort(key=lambda it: (1 if it[3] else 0, it[2], it[4]), reverse=True)
    evict = items[budget:]
    evicted_count = 0
    for st_key, f_key, _n, protected, _last_ev, entry in evict:
        if protected:
            continue
        slot = archived.setdefault(st_key, {})
        slot[f_key] = dict(entry, archived_reason='finite_budget_interference_eviction')
        del state['comprehension'][st_key][f_key]
        if not state['comprehension'][st_key]:
            del state['comprehension'][st_key]
        evicted_count += 1

    active_after = sum(len(fmap) for k, fmap in state['comprehension'].items()
                       if not speaker or k.startswith(speaker + ':'))
    protected_after = sum(
        1 for k, fmap in state['comprehension'].items()
        if not speaker or k.startswith(speaker + ':')
        for e in fmap.values() if e.get('protected')
    )
    return {
        'active_count': active_after,
        'protected_count': protected_after,
        'evicted_to_archive': evicted_count,
    }


def record_interference_exposure(path, listener, speaker, token, feature_key, source_tag='interference'):
    """Record a single-exposure interference association and enforce the finite memory budget."""
    dev, _, storage = _lazy_deps()
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state, _ = _community_contract(db, listener)
        state['version'] += 1
        ident = f'interf-{listener}-{state["version"]}'
        payload = {
            'run_id': state['run_id'],
            'agent': listener,
            'speaker': speaker,
            'token': token,
            'feature': feature_key,
            'source_tag': source_tag,
            'grounded': True,
            'scaffolding': 'bounded interference exposure',
        }
        dev._record(db, ident, listener, 'interference_exposure', payload)
        assoc = state['comprehension'].setdefault(f'{speaker}:{token}', {})
        entry = assoc.setdefault(feature_key, {'n': 0, 'evidence': [], 'protected': False})
        entry['n'] += 1
        entry['protected'] = entry['n'] >= int(state.get('protection_threshold', DEFAULT_PROTECTION_THRESHOLD))
        entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        budget_report = enforce_memory_budget(state, speaker=speaker)
        dev._put(db, 'development_people', listener, state)
        db.commit()
        return {'record_id': ident, 'budget_report': budget_report}


def audit(path):
    _, symbols, storage = _lazy_deps()
    base = symbols.audit(path)
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        community_summary = {}
        for agent, state in base['people'].items():
            _, contract = _community_contract(db, agent)
            active_slots = sum(len(v) for v in state['comprehension'].values())
            protected_slots = sum(
                1 for fmap in state['comprehension'].values()
                for e in fmap.values() if int(e.get('n', 0)) >= int(state.get('protection_threshold', DEFAULT_PROTECTION_THRESHOLD))
            )
            archived_slots = sum(len(v) for v in state.get('archived_comprehension', {}).values())
            community_summary[agent] = {
                'community_id': state.get('community_id', contract.get('community_id')),
                'cohort_role': state.get('cohort_role', contract.get('cohort_role')),
                'active_budget': state.get('active_budget', DEFAULT_ACTIVE_BUDGET),
                'active_associations': active_slots,
                'protected_associations': protected_slots,
                'archived_associations': archived_slots,
                'vocabulary_hash': symbols.vocabulary_hash(state),
            }
    base['community'] = community_summary
    return base
