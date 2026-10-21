"""Private coined symbols grounded in own native perception, never a shared lexicon."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path

from . import developmental as dev, storage
from .lease import Lease
from .wire import dumps

ALPHABET = tuple(f's{i:02x}' for i in range(16))  # Channel IDs only; no meanings.


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _contract(db, agent):
    state = dev._person(db, agent, agent)
    ident = 'signal-contract-' + agent
    row = db.execute('SELECT payload,checksum FROM development_records WHERE id=? AND agent=?',
                     (ident, agent)).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
        raise ValueError('missing private symbol contract')
    contract = json.loads(row[0])
    if contract['module_sha256'] != module_hash():
        raise ValueError('symbol mechanism source mismatch; original runtime required')
    return state


def initialize(path, seed=41, population=4):
    dev.initialize(path, seed=seed, population=population)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent, in db.execute('SELECT agent FROM development_people').fetchall():
            state = dev._person(db, agent, agent)
            state['symbol_control_seed'] = int(hashlib.sha256(f'{seed}:{agent}:symbol-control'.encode()).hexdigest()[:16],16)
            dev._put(db, 'development_people', agent, state)
            dev._record(db, 'signal-contract-' + agent, agent, 'channel_contract', {
                'run_id': state['run_id'], 'agent': agent, 'module_sha256': module_hash(),
                'channel': {'symbols': 16, 'max_tokens': 1, 'delivery': 'native_speak'},
                'feedback': 'own visible mass change; authored demonstration scaffolding'})
        db.commit()
    return audit(path)


def percept(entity):
    return dumps([hashlib.sha256(entity['kind'].encode()).hexdigest()[:12],
                  math.floor(int(entity['mass_ug']) / 100000000)])


def _visible(observation, candidates):
    return {e['entity_id']: e for e in observation['visible_entities'] if e['entity_id'] in candidates}


def coin(path, agent, target):
    """A private naming affordance: current own percept plus saved random choice."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, head = storage._head(db)
        o = world.observe_batch([agent])[0]
        state = _contract(db, agent)
        entity = _visible(o, [target]).get(target)
        if not entity:
            raise ValueError('coining requires an own visible referent')
        key = percept(entity)
        if key not in state['production']:
            used = {v['token'] for v in state['production'].values()}
            options = [token for token in ALPHABET if token not in used]
            if not options:
                raise ValueError('private symbol alphabet exhausted')
            token = options[dev.random_index(state, len(options))]
            state['version'] += 1
            ident = f'coin-{agent}-{state["version"]}'
            dev._record(db, ident, agent, 'coining', {'run_id': state['run_id'], 'agent': agent,
                'observation': o, 'native_head': head, 'feature': key, 'token': token,
                'origin': 'private_seeded_coinage', 'meaning_not_publicly_validated': True})
            state['production'][key] = {'token': token, 'evidence': [ident]}
            dev._put(db, 'development_people', agent, state)
        else:
            token = state['production'][key]['token']
        db.commit()
        return token


def production_token(path, agent, target):
    """Frozen production: never invent a missing symbol during scored trials."""
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        world, _, _, _ = storage._head(db)
        state = _contract(db, agent)
        o = world.observe_batch([agent])[0]
        entity = _visible(o, [target]).get(target)
        if not entity or percept(entity) not in state['production']:
            raise ValueError('unknown own referent; frozen production has no symbol')
        for ident in state['production'][percept(entity)]['evidence']:
            row = db.execute('SELECT payload,checksum FROM development_records WHERE id=? AND agent=?', (ident,agent)).fetchone()
            if not row or hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:
                raise ValueError('missing private coining evidence')
        return state['production'][percept(entity)]['token']


def begin_attention(path, listener, candidates):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, head = storage._head(db)
        o = world.observe_batch([listener])[0]
        state = _contract(db, listener)
        if set(_visible(o, candidates)) != set(candidates):
            raise ValueError('attention requires all demonstrated alternatives visible')
        if state.get('attention'):
            raise ValueError('finish the current private attention window first')
        state['attention'] = {'before': o, 'candidates': list(candidates), 'head': head,
            'last_heard_seq': max((int(r['source_event_seq']) for r in o['audible_reports']), default=0)}
        dev._put(db, 'development_people', listener, state)
        db.commit()


def _heard(observation, speaker, after_seq=0):
    reports = [r for r in observation['audible_reports'] if r['speaker_id'] == speaker and
               r['text'] in ALPHABET and int(r['source_event_seq']) > after_seq]
    return max(reports, key=lambda r: int(r['source_event_seq'])) if reports else None


def learn_attention(path, listener, speaker):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, head = storage._head(db)
        o = world.observe_batch([listener])[0]
        state = _contract(db, listener)
        attention = state.get('attention')
        if not attention:
            raise ValueError('own prior attention observation required')
        before = _visible(attention['before'], attention['candidates'])
        after = _visible(o, attention['candidates'])
        changed = [ident for ident in before if ident in after and
                   int(after[ident]['mass_ug']) - int(before[ident]['mass_ug']) == 1000000]
        other_changes = [ident for ident in before if ident not in after or
                         int(after[ident]['mass_ug']) != int(before[ident]['mass_ug'])]
        report = _heard(o, speaker, attention['last_heard_seq'])
        grounded = len(changed) == 1 and other_changes == changed and report is not None
        state['version'] += 1
        ident = f'ground-{listener}-{state["version"]}'
        source = dev._source_events(db, path, [report['source_event_seq']]) if report else {}
        if report:
            event = source[report['source_event_seq']]
            if event['type'] != 'speech' or event['agent_id'] != speaker or event['detail'] != report['text']:
                raise ValueError('delivered token does not match native speech proof')
        feedback = {'run_id': state['run_id'], 'agent': listener, 'before': attention['before'],
                    'after': o, 'source_heads': [attention['head'], head], 'message': report,
                    'native_events': source, 'grounded': grounded,
                    'scaffolding': 'authored physical deposit demonstration; no hidden target lookup'}
        if grounded:
            key = percept(before[changed[0]])
            association = state['comprehension'].setdefault(speaker + ':' + report['text'], {})
            entry = association.setdefault(key, {'n': 0, 'evidence': []})
            entry['n'] += 1
            entry['evidence'] = (entry['evidence'] + [ident])[-16:]
            feedback['observed_feature'] = key
        dev._record(db, ident, listener, 'grounding', feedback)
        state.pop('attention')
        dev._put(db, 'development_people', listener, state)
        db.commit()
        return feedback


def select_reference(path, listener, speaker, candidates, after_seq=0, mode='learned'):
    """No intended target or speaker private vocabulary argument exists."""
    if mode not in ('learned', 'silence', 'random'):
        raise ValueError('unknown private interpretation mode')
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        o = world.observe_batch([listener])[0]
        state = _contract(db, listener)
        visible = _visible(o, candidates)
        if set(visible) != set(candidates):
            raise ValueError('reference alternatives must be currently visible')
        message = _heard(o, speaker, after_seq)
        if mode != 'silence' and not message:
            raise ValueError('no new natively delivered token; reference is unknown')
        association = state['comprehension'].get(speaker + ':' + message['text'], {}) if message else {}
        features = sorted({percept(e) for e in visible.values()})
        scores = {}
        for ident, entity in visible.items():
            key = percept(entity)
            if mode == 'silence':
                score = 0
            elif mode == 'random':
                # Private fixed random control, never written into a learned vocabulary.
                index = int(hashlib.sha256(f'{state["symbol_control_seed"]}:{listener}:{message["text"]}'.encode()).hexdigest()[:8],16) % len(features)
                score = int(key == features[index])
            else:
                entry = association.get(key, {'n': 0, 'evidence': []})
                for source_id in entry['evidence']:
                    row = db.execute('SELECT payload,checksum FROM development_records WHERE id=? AND agent=?',
                                     (source_id, listener)).fetchone()
                    if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
                        raise ValueError('missing private grounding evidence')
                    proof = json.loads(row[0])
                    if dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
                        raise ValueError('missing native grounding chain')
                score = entry['n']
            scores[ident] = score
        best = max(scores.values())
        options = sorted(ident for ident, value in scores.items() if value == best)
        target = options[dev.random_index(state, len(options))]
        dev._put(db, 'development_people', listener, state)
        db.commit()
        return {'target': target, 'message': message, 'scores': scores, 'mode': mode,
                'observation_version': o['observation_version'], 'origin': 'private_symbol_interpretation'}


def vocabulary_hash(state):
    return dev.digest({k: state[k] for k in ('production', 'comprehension')})


def audit(path):
    result = dev.audit(path)
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        for agent in result['people']:
            _contract(db, agent)
        for payload, in db.execute("SELECT payload FROM development_records WHERE kind='grounding'"):
            proof=json.loads(payload)
            if dev._source_events(db,path,list(proof['native_events']))!=proof['native_events']:
                raise ValueError('native grounding source mismatch')
    result['vocabulary_hashes'] = {a: vocabulary_hash(s) for a,s in result['people'].items()}
    return result
