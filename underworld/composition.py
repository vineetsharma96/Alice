"""Opt-in H5: authored factorization, privately coined unordered native sequences."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re

from . import developmental as dev, storage, symbols, wayfinding as wf
from .lease import Lease

LIMITS = {'tokens': 2, 'production': 16, 'hypotheses': 64, 'messages': 64, 'evidence': 16}


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def parse(text):
    if not isinstance(text, str) or not re.fullmatch(r's[0-9a-f]{2}( s[0-9a-f]{2})?', text):
        raise ValueError('H5 requires one or two distinct channel IDs')
    tokens = text.split(' ')
    if len(set(tokens)) != len(tokens) or any(t not in symbols.ALPHABET for t in tokens):
        raise ValueError('H5 requires one or two distinct channel IDs')
    return tokens


def features(entity):
    # These two sensory axes and their factorization are authored priors.
    return ['category:' + hashlib.sha256(entity['kind'].encode()).hexdigest()[:12],
            'mass:' + str(int(entity['mass_ug']) // 100000000)]


def _person(db, agent):
    state = wf._person(db, agent)
    contract = dev._read(db, 'development_records', 'composition-contract-' + agent, 'id')
    if (contract['module_sha256'], contract['agent'], contract['run_id'], contract['limits']) != (
            module_hash(), agent, state['run_id'], LIMITS):
        raise ValueError('H5 mechanism/identity mismatch; original runtime required')
    h = state['h5']
    for key, limit in [('production', 16), ('hypotheses', 64), ('messages', 64)]:
        if len(h[key]) > limit:
            raise ValueError('H5 private budget exceeded')
    if len({v['token'] for v in h['production'].values()}) != len(h['production']):
        raise ValueError('H5 private production collision')
    path = Path(db.execute('PRAGMA database_list').fetchone()[2])
    for feature, entry in h['production'].items():
        p = dev._read(db, 'development_records', entry['evidence'], 'id')
        if p['agent'] != agent or p['feature'] != feature or p['token'] != entry['token'] or feature not in features(_entity(p['observation'], p['target'])):
            raise ValueError('H5 private coin evidence mismatch')
    for channel, entry in h['hypotheses'].items():
        if not entry['evidence'] or len(entry['evidence']) != min(16, entry['n']):
            raise ValueError('H5 hypothesis proof count mismatch')
        for ident in entry['evidence']:
            p = dev._read(db, 'development_records', ident, 'id')
            message = p['message']
            if (p['agent'] != agent or message['speaker_id'] + ':' + channel.split(':', 1)[1] != channel or
                    channel.split(':', 1)[1] not in parse(message['text']) or
                    not set(entry['possible']) <= set(p['observed_features'])):
                raise ValueError('H5 private hypothesis source mismatch')
            if dev._source_events(db, path, list(p['native_events'])) != p['native_events']:
                raise ValueError('H5 native hypothesis source missing')
            wf._proof(db, path, message)
    for key, entry in h['messages'].items():
        speaker, tokens, values = json.loads(key)
        if not entry['evidence'] or len(entry['evidence']) != min(16, entry['n']):
            raise ValueError('H5 message proof count mismatch')
        for ident in entry['evidence']:
            p = dev._read(db, 'development_records', ident, 'id')
            if (p['agent'], p['message']['speaker_id'], sorted(parse(p['message']['text'])), p['observed_features']) != (agent, speaker, tokens, values):
                raise ValueError('H5 whole-message source mismatch')
            wf._proof(db, path, p['message'])
    return state


def _record(db, state, ident, kind, payload):
    payload = json.loads(dev.dumps(dict(payload, agent=state['agent'], run_id=state['run_id'])))
    dev._record(db, ident, state['agent'], 'h5_' + kind, payload)
    state['version'] += 1
    dev._put(db, 'development_people', state['agent'], state)
    return dict(payload, record_id=ident)


def initialize(path, seed=47):
    wf.initialize(path, seed)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent, in db.execute('SELECT agent FROM development_people').fetchall():
            state = wf._person(db, agent)
            state['h5'] = dict(production={}, hypotheses={}, messages={}, attention=None,
                               external_teaching=0, authored_decisions=0, random_ties=0,
                               protective_fallbacks=0)
            dev._record(db, 'composition-contract-' + agent, agent, 'h5_contract', dict(
                agent=agent, run_id=state['run_id'], module_sha256=module_hash(), limits=LIMITS,
                prior='authored category/mass factor encoder; unordered intersection learner',
                channel='separate H5 native speak; one simulated second per token'))
            dev._put(db, 'development_people', agent, state)
        db.commit()
    return audit(path)


def private(path, agent, principal):
    if agent != principal:
        raise ValueError('private H5 access denied')
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        return _person(db, agent)['h5']


def _entity(observation, target):
    entity = next((e for e in observation['visible_entities'] if e['entity_id'] == target), None)
    if not entity or entity['kind'] not in ('food', 'water'):
        raise ValueError('H5 referent must be own visible food or water')
    return entity


def encode(path, agent, target, learn=False):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        world, _, _, head = storage._head(db)
        observation = world.observe_batch([agent])[0]
        values = features(_entity(observation, target))
        production = state['h5']['production']
        for value in values:
            if value not in production:
                if not learn:
                    raise ValueError('unknown private factor; frozen production')
                options = [t for t in symbols.ALPHABET if t not in {e['token'] for e in production.values()}]
                if not options:
                    raise ValueError('H5 private alphabet exhausted')
                token = options[dev.random_index(state, len(options))]
                ident = f'h5-coin-{agent}-{state["version"] + 1}'
                production[value] = {'token': token, 'evidence': ident}
                _record(db, state, ident, 'coin', dict(feature=value, token=token,
                    observation=observation, native_head=head, target=target,
                    origin='authored factorization; private random coinage'))
        tokens = [production[v]['token'] for v in values]
        if dev.random_index(state, 2):
            tokens.reverse()
        dev._put(db, 'development_people', agent, state)
        db.commit()
        return ' '.join(tokens)


def send(path, agent, message_id, text, fault=None):
    """Idempotent logical message bound to exactly one durable native request.

    Single writer lease spans reservation/reconciliation. Other actor actions can
    make an unsubmitted intent stale; recovery refuses rather than guessing.
    """
    tokens = parse(text)
    if not isinstance(message_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', message_id):
        raise ValueError('invalid H5 message identity')
    ident = f'h5-send-{agent}-{message_id}'
    with Lease(path):
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent)
            row = db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone()
            if row:
                intent = dev._read(db, 'development_records', ident, 'id')
                if intent['text'] != text:
                    raise ValueError('conflicting H5 message identity')
                if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident + '-receipt',)).fetchone():
                    return dict(dev._read(db, 'development_records', ident + '-receipt', 'id'), record_id=ident + '-receipt')
            else:
                outstanding = state['h5'].get('pending_message')
                if outstanding or db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone():
                    raise ValueError('reconcile pending H5/native message first')
                if db.execute('SELECT COUNT(*) FROM development_records WHERE agent=?', (agent,)).fetchone()[0] > dev.QUOTA - 3:
                    raise ValueError('H5 evidence quota: reserve intent, native experience and receipt first')
                world, _, _, head = storage._head(db)
                intent = dict(text=text, request_id=f'dev-{agent}-{state["counter"] + 1}',
                              observation_version=world.observe_batch([agent])[0]['observation_version'],
                              native_head=head, tokens=len(tokens))
                state['h5']['pending_message'] = ident
                _record(db, state, ident, 'send_intent', intent)
                intent = dev._read(db, 'development_records', ident, 'id')
            db.commit()
        if fault:
            fault('after_message_intent')
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute('BEGIN')
            row = db.execute('SELECT 1 FROM development_records WHERE id=?', (intent['request_id'],)).fetchone()
            pending = db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone()
            state = _person(db, agent)
            if row:
                experience = dev._read(db, 'development_records', intent['request_id'], 'id')
            elif pending:
                p = dev._read(db, 'development_pending', agent, 'agent')
                if p['request']['request_id'] != intent['request_id'] or p['request']['parameters'] != {'text': text}:
                    raise ValueError('H5 pending native identity mismatch')
            elif f'dev-{agent}-{state["counter"] + 1}' != intent['request_id'] or dev.own_observation(path, agent)['observation_version'] != intent['observation_version']:
                raise ValueError('unsubmitted H5 intent at changed head; explicit recovery required')
        if not row:
            experience = (dev.reconcile(path, agent, fault=fault) if pending else
                dev.execute(path, agent, 'speak', parameters={'text': text}, duration=len(tokens),
                            prediction={'h5_message': ident}, update_memory=False, fault=fault))
        if experience['request']['parameters'] != {'text': text} or experience['request']['action_type'] != 'speak':
            raise ValueError('H5 native request conflict')
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent)
            if state['h5'].get('pending_message') == ident:
                state['h5'].pop('pending_message')
            result = _record(db, state, ident + '-receipt', 'sent', dict(
                message_id=message_id, text=text, request_id=intent['request_id'],
                status=experience['receipt']['status'], native_events=experience['native_events']))
            db.commit()
        return result


def begin(path, listener, attention_id, candidates):
    if not isinstance(attention_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', attention_id):
        raise ValueError('invalid H5 attention identity')
    if not 1 <= len(candidates) <= 16 or len(set(candidates)) != len(candidates):
        raise ValueError('H5 attention requires 1..16 distinct candidates')
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, listener)
        if state['h5']['attention']:
            raise ValueError('finish pending H5 attention first')
        ident = f'h5-learn-{listener}-{attention_id}'
        if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone():
            raise ValueError('H5 attention identity already learned')
        world, _, _, head = storage._head(db)
        o = world.observe_batch([listener])[0]
        for target in candidates:
            _entity(o, target)
        state['h5']['attention'] = dict(id=attention_id, before=o, candidates=list(candidates), head=head,
            after_seq=max((int(r['source_event_seq']) for r in o['audible_reports']), default=0))
        dev._put(db, 'development_people', listener, state)
        db.commit()


def _heard(o, speaker, after_seq):
    reports = [r for r in o['audible_reports'] if r['speaker_id'] == speaker and int(r['source_event_seq']) > after_seq]
    if not reports:
        raise ValueError('no new native H5 utterance')
    report = max(reports, key=lambda r: int(r['source_event_seq']))
    parse(report['text'])
    return report


def learn(path, listener, speaker, attention_id, fault=None):
    ident = f'h5-learn-{listener}-{attention_id}'
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, listener)
        if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone():
            result = dev._read(db, 'development_records', ident, 'id')
            if result['message']['speaker_id'] != speaker:
                raise ValueError('conflicting H5 learning identity')
            return dict(result, record_id=ident)
        a = state['h5']['attention']
        if not a or a['id'] != attention_id:
            raise ValueError('own pending H5 attention required')
        world, _, _, head = storage._head(db)
        o = world.observe_batch([listener])[0]
        before = {t: _entity(a['before'], t) for t in a['candidates']}
        after = {t: _entity(o, t) for t in a['candidates']}
        changes = [t for t in before if int(after[t]['mass_ug']) != int(before[t]['mass_ug'])]
        if len(changes) != 1 or int(after[changes[0]]['mass_ug']) - int(before[changes[0]]['mass_ug']) != 1000000:
            raise ValueError('H5 grounding requires exactly one native .001kg deposit')
        message = _heard(o, speaker, a['after_seq'])
        events = wf._proof(db, path, message)
        values = features(before[changes[0]])
        tokens = parse(message['text'])
        h = state['h5']
        for token in tokens:
            key = speaker + ':' + token
            entry = h['hypotheses'].setdefault(key, dict(possible=values, n=0, evidence=[]))
            entry['possible'] = sorted(set(entry['possible']) & set(values))
            entry['n'] += 1
            entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        key = dev.dumps([speaker, sorted(tokens), values])
        entry = h['messages'].setdefault(key, dict(n=0, evidence=[]))
        entry['n'] += 1
        entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        if len(h['hypotheses']) > 64 or len(h['messages']) > 64:
            raise ValueError('H5 association budget exhausted')
        h['attention'] = None
        h['external_teaching'] += 1
        result = _record(db, state, ident, 'learning', dict(before=a['before'], after=o,
            source_heads=[a['head'], head], candidates=a['candidates'], observed_features=values,
            message=message, native_events=events, origin='authored physical deposit joint attention'))
        if fault:
            fault('before_learning_commit')
        db.commit()
        if fault:
            fault('after_learning_commit')
        return result


def select(path, listener, speaker, candidates, after_seq=0, mode='learned'):
    if mode not in ('learned', 'whole', 'muted'):
        raise ValueError('invalid H5 interpretation mode')
    if not 1 <= len(candidates) <= 16 or len(set(candidates)) != len(candidates):
        raise ValueError('H5 reference requires 1..16 distinct candidates')
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, listener)
        world, _, _, _ = storage._head(db)
        o = world.observe_batch([listener])[0]
        message = _heard(o, speaker, after_seq) if mode != 'muted' else None
        events = wf._proof(db, path, message) if message else {}
        tokens = parse(message['text']) if message else []
        h = state['h5']
        scores = {}
        for target in candidates:
            values = features(_entity(o, target))
            if mode == 'whole':
                score = h['messages'].get(dev.dumps([speaker, sorted(tokens), values]), {}).get('n', 0)
            else:
                score = 0
                for token in tokens:
                    possible = h['hypotheses'].get(speaker + ':' + token, {}).get('possible', [])
                    if possible:
                        score += len(set(values) & set(possible)) / len(possible)
            scores[target] = score
        options = sorted(t for t, score in scores.items() if score == max(scores.values()))
        target = options[dev.random_index(state, len(options))]
        h['authored_decisions'] += 1
        h['random_ties'] += int(len(options) > 1)
        result = _record(db, state, f'h5-response-{listener}-{state["version"] + 1}', 'response', dict(
            target=target, scores=scores, message=message, mode=mode, observation=o,
            native_events=events, random_tie=len(options) > 1,
            origin='authored overlap rule using private learned hypotheses'))
        db.commit()
        return result


def audit(path):
    result = wf.audit(path)
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        for agent in result['people']:
            state = _person(db, agent)
            h = state['h5']
            hypotheses, messages = {}, {}
            proofs = db.execute("SELECT id,payload FROM development_records WHERE agent=? AND kind LIKE 'h5_%' ORDER BY rowid", (agent,)).fetchall()
            for ident, raw in proofs:
                proof = json.loads(raw)
                if proof['agent'] != agent or proof['run_id'] != state['run_id']:
                    raise ValueError('H5 source owner mismatch')
                if 'native_events' in proof and dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
                    raise ValueError('H5 native source mismatch')
                if ident.startswith('h5-learn-'):
                    tokens = parse(proof['message']['text'])
                    before = {t: _entity(proof['before'], t) for t in proof['candidates']}
                    after = {t: _entity(proof['after'], t) for t in proof['candidates']}
                    changed = [t for t in before if int(before[t]['mass_ug']) != int(after[t]['mass_ug'])]
                    if len(changed) != 1 or int(after[changed[0]]['mass_ug']) - int(before[changed[0]]['mass_ug']) != 1000000:
                        raise ValueError('H5 physical grounding mismatch')
                    values = features(before[changed[0]])
                    if values != proof['observed_features']:
                        raise ValueError('H5 private learned feature mismatch')
                    speaker = proof['message']['speaker_id']
                    wf._proof(db, path, proof['message'])
                    for token in tokens:
                        e = hypotheses.setdefault(speaker + ':' + token, dict(possible=values, n=0, evidence=[]))
                        e['possible'] = sorted(set(e['possible']) & set(values))
                        e['n'] += 1
                        e['evidence'] = (e['evidence'] + [ident])[-16:]
                    e = messages.setdefault(dev.dumps([speaker, sorted(tokens), values]), dict(n=0, evidence=[]))
                    e['n'] += 1
                    e['evidence'] = (e['evidence'] + [ident])[-16:]
            if (hypotheses, messages) != (h['hypotheses'], h['messages']):
                raise ValueError('H5 learned associations disagree with private evidence')
            for feature, entry in h['production'].items():
                p = dev._read(db, 'development_records', entry['evidence'], 'id')
                if p['agent'] != agent or p['feature'] != feature or p['token'] != entry['token'] or feature not in features(_entity(p['observation'], p['target'])):
                    raise ValueError('H5 private coin evidence mismatch')
    result['h5_memory_hashes'] = {a: dev.digest({k: s['h5'][k] for k in ('production', 'hypotheses', 'messages')}) for a, s in result['people'].items()}
    return result
