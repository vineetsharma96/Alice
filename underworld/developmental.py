"""Opt-in incremental source-affordance research, independent of Phase9/G policies."""
import argparse
from contextlib import closing
import copy
import hashlib
import json
import math
from pathlib import Path

from . import storage, runtime
from .config import load
from .lease import Lease
from .wire import dumps

ROOT = Path(__file__).resolve().parents[1]
MECHANISM = 'developmental-1'
QUOTA = 2048
PRIORS = {
    'sensory': 'native own observations; categorical hash; coarse mass/range bins',
    'motor': 'native gather/inspect/move/deposit/speak; authored action vocabulary',
    'update': 'count observable goal outcomes; Beta(1,1) mean heuristic',
    'exploration': 'bounded authored curriculum; saved private random tie breaks',
    'protection': 'unchanged native bodies; short scaffolded research, not independent survival',
    'initial_absences': ['outcome_tables', 'validated_procedures', 'symbol_meanings', 'partner_vocabulary'],
    'external_sources': 'operator-introduced native sources recorded separately',
    'limits': {'experiences_per_person': QUOTA, 'alphabet': 16, 'utterance_tokens': 1},
}


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def source_files():
    return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
            for n in ('underworld/developmental.py', 'config/developmental.toml')}


def _read(db, table, key, column):
    row = db.execute(f'SELECT payload,checksum FROM {table} WHERE {column}=?', (key,)).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
        raise ValueError('developmental missing record or checksum mismatch')
    return json.loads(row[0])


def _put(db, table, key, value):
    text = dumps(value)
    db.execute(f'INSERT OR REPLACE INTO {table} VALUES(?,?,?)',
               (key, text, hashlib.sha256(text.encode()).hexdigest()))


def _meta(db):
    value = _read(db, 'development_meta', 1, 'singleton')
    if value['mechanism'] != MECHANISM or value['source_files'] != source_files():
        raise ValueError('developmental source mismatch; preserve and use its original runtime')
    if value['run_id'] != db.execute('SELECT run_id FROM run').fetchone()[0]:
        raise ValueError('developmental run identity mismatch')
    if runtime.verify_control(db)['epoch']:
        runtime.verify_archives(Path(db.execute('PRAGMA database_list').fetchone()[2]))
    return value


def _person(db, agent, principal):
    if agent != principal:
        raise ValueError('private learner access denied')
    meta = _meta(db)
    value = _read(db, 'development_people', agent, 'agent')
    if value['agent'] != agent or value['run_id'] != meta['run_id']:
        raise ValueError('private learner identity mismatch')
    return value


def random_index(state, count):
    if count < 1:
        raise ValueError('empty choice set')
    state['rng'] = (state['rng'] * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
    return (state['rng'] >> 16) % count


def initialize(path, config=None, seed=None, population=None, profile='novice-affordance'):
    if profile != 'novice-affordance':
        raise ValueError('unknown explicit developmental profile')
    config = copy.deepcopy(config or load(ROOT / 'config/developmental.toml'))
    if seed is not None:
        config['seed'] = seed
    if population is not None:
        config['world']['population'] = population
    if config['cognition']['provider'] != 'disabled' or config.get('agency', {}).get('policy') != 'none':
        raise ValueError('developmental research requires model-off, explicit action scheduling')
    storage.create(path, config, scripted=False)
    with Lease(path), closing(storage._connect(path)) as db:
        db.executescript('''
            CREATE TABLE development_meta(singleton INTEGER PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE TABLE development_people(agent TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE TABLE development_pending(agent TEXT PRIMARY KEY,payload TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE TABLE development_records(id TEXT PRIMARY KEY,agent TEXT NOT NULL,kind TEXT NOT NULL,
                payload TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE INDEX development_owner ON development_records(agent,kind,id);
        ''')
        db.execute('BEGIN IMMEDIATE')
        run = db.execute('SELECT run_id FROM run').fetchone()[0]
        _put(db, 'development_meta', 1, {'mechanism': MECHANISM, 'run_id': run,
             'priors': PRIORS, 'source_files': source_files(), 'schema': 1,
             'profile': profile,
             'people': [f'agent-{i+1}' for i in range(config['world']['population'])]})
        for i in range(config['world']['population']):
            agent = f'agent-{i+1}'
            rng = int(hashlib.sha256(f'{config["seed"]}:{agent}:{MECHANISM}'.encode()).hexdigest()[:16], 16)
            _put(db, 'development_people', agent, {'mechanism': MECHANISM, 'agent': agent,
                 'run_id': run, 'profile': profile, 'rng': rng, 'version': 0, 'counter': 0, 'associations': {},
                 'objects': {}, 'production': {}, 'comprehension': {}, 'procedures': [],
                 'experiences': 0, 'external_teaching': 0, 'protective_fallbacks': 0})
        db.commit()
    return audit(path)


def _record(db, ident, agent, kind, value):
    text = dumps(value)
    old = db.execute('SELECT payload FROM development_records WHERE id=?', (ident,)).fetchone()
    if old:
        if old[0] != text:
            raise ValueError('conflicting developmental evidence identity')
        return
    if db.execute('SELECT COUNT(*) FROM development_records WHERE agent=?', (agent,)).fetchone()[0] >= QUOTA:
        raise ValueError('developmental evidence quota reached')
    db.execute('INSERT INTO development_records VALUES(?,?,?,?,?)',
               (ident, agent, kind, text, hashlib.sha256(text.encode()).hexdigest()))


def private_state(path, agent, principal):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        storage._head(db)
        return _person(db, agent, principal)


def own_observation(path, agent):
    return storage.observe(path, [agent])[0]


def sensory(entity, own):
    category = hashlib.sha256(entity['kind'].encode()).hexdigest()[:12]
    mass = int(entity['mass_ug']) / 1e9
    distance = math.dist(entity['position_m'], own['position_m'])
    return dumps([category, 'zero' if mass == 0 else 'trace' if mass < .01 else 'stock',
                  'near' if distance < 2 else 'far'])


def _association(state, key, object_key=None):
    return (state['objects'].get(object_key) if object_key is not None else
            state['associations'].get(key)) or {'n': 0, 'successes': 0, 'evidence': []}


def _archives(db, path):
    verified = runtime.verify_archives(path)
    rows = db.execute('SELECT payload FROM runtime_epochs ORDER BY epoch DESC LIMIT ?',
                      (verified['verified_retained'],)).fetchall()
    return [Path(str(path) + '.epochs') / json.loads(row[0])['archive'] for row in rows]


def _source_events(db, path, references):
    found = {}
    for reference in references:
        row = db.execute('SELECT payload FROM events WHERE seq=?', (int(reference),)).fetchone()
        if row:
            found[reference] = json.loads(row[0])
    if len(found) < len(set(references)):
        for file in _archives(db, path):
            with closing(storage._connect(file, readonly=True)) as archived:
                for reference in set(references) - set(found):
                    row = archived.execute('SELECT payload FROM events WHERE seq=?', (int(reference),)).fetchone()
                    if row:
                        found[reference] = json.loads(row[0])
    if len(found) != len(set(references)):
        raise ValueError('missing native evidence chain; outcome is unknown')
    return found


def _fingerprint(db):
    return digest({table: db.execute(f'SELECT * FROM {table} ORDER BY 1').fetchall()
                   for table in ('development_meta', 'development_people', 'development_records', 'development_pending')})


def archive(path, fault=None):
    """Verify the learner snapshot before native pruning; protect required epochs."""
    path = Path(path).resolve()
    with Lease(path), closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        _, config, _, _ = storage._head(db)
        _meta(db)
        if db.execute('SELECT 1 FROM development_pending').fetchone():
            raise ValueError('reconcile developmental pending intents before archival')
        before = _fingerprint(db)
        control = runtime.verify_control(db)
        limits = config.get('execution', runtime.DEFAULTS)
        retained = _archives(db, path)
        # New backup preserves live events. Only the newest keep-1 old epochs
        # will remain. Refuse eviction if any protected native proof would vanish.
        available = {str(r[0]) for r in db.execute('SELECT seq FROM events')}
        for file in retained[:limits['checkpoint_keep']-1]:
            with closing(storage._connect(file, readonly=True)) as archived:
                available.update(str(r[0]) for r in archived.execute('SELECT seq FROM events'))
        required = set()
        for payload, in db.execute('SELECT payload FROM development_records'):
            required.update(json.loads(payload).get('native_events', {}))
        if not required <= available:
            raise ValueError('developmental protected source archive quota reached')
        output = Path(str(path) + '.epochs') / f'epoch-{control["epoch"]+1:08d}.sqlite'
        db.rollback()  # Release the read transaction before the native writer commits.
        def verify_snapshot(stage, tick):
            if stage == 'after_checkpoint':
                with closing(storage._connect(output, readonly=True)) as saved:
                    if _fingerprint(saved) != before:
                        raise ValueError('unfinished archive has different developmental state')
            if fault:
                fault(stage, tick)
        return runtime.rotate(path, limits, fault=verify_snapshot)


def _prediction(db, path, state, key, object_key=None):
    association = _association(state, key, object_key)
    missing = False
    for ident in association['evidence']:
        row = db.execute('SELECT payload,checksum FROM development_records WHERE id=? AND agent=?',
                         (ident, state['agent'])).fetchone()
        if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            missing = True
            break
        proof = json.loads(row[0])
        try:
            if _source_events(db, path, proof['receipt']['event_refs']) != proof['native_events']:
                missing = True
        except ValueError:
            missing = True
    n = 0 if missing else association['n']
    successes = 0 if missing else association['successes']
    return {'feature': key, 'n': n, 'successes': successes, 'mean': (successes + 1) / (n + 2),
            'evidence': association['evidence'], 'uncertain_missing_source': missing,
            'origin': 'object_memory' if object_key is not None else 'learned_feature_counts'}


def choose(path, agent, candidates, mode='learning'):
    if mode not in ('learning', 'frozen', 'memory', 'authored'):
        raise ValueError('unknown developmental comparator')
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        o = world.observe_batch([agent])[0]
        state = _person(db, agent, agent)
        entities = [e for e in o['visible_entities'] if e['entity_id'] in candidates]
        predictions = []
        for e in entities:
            key = sensory(e, o['own_state'])
            p = _prediction(db, path, state, key, e['entity_id'] if mode == 'memory' else None)
            if mode == 'frozen':
                p = dict(p, n=0, successes=0, mean=.5, evidence=[], origin='frozen_initial')
            if mode == 'authored':
                p['mean'] = float(e['kind'] == 'food' and e['radius_m'] == 0 and
                    int(e['mass_ug']) >= 1000000 and
                    math.dist(e['position_m'], o['own_state']['position_m']) <= 1.5 and
                    int(o['own_state']['carried_mass_ug']) + 1000000 <= 2000000000)
                p['origin'] = 'strong_authored_validator_aware_baseline'
            predictions.append(dict(p, target=e['entity_id']))
        best = max((p['mean'] for p in predictions), default=0)
        options = [p for p in predictions if p['mean'] == best]
        selected = options[random_index(state, len(options))] if options and best >= .5 else None
        _put(db, 'development_people', agent, state)
        db.commit()
        return {'target': selected['target'] if selected else None, 'predictions': predictions,
                'observation_version': o['observation_version'], 'origin': mode,
                'uncertainty_rule': 'abstain if every predicted mean is below0.5'}


def execute(path, agent, action, targets=(), parameters=None, duration=1, learn_food=False,
            prediction=None, fault=None, update_memory=True):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        state = _person(db, agent, agent)
        if db.execute('SELECT COUNT(*) FROM development_records WHERE agent=?', (agent,)).fetchone()[0] >= QUOTA:
            raise ValueError('developmental evidence quota reached before physical execution')
        if db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone():
            raise ValueError('reconcile the pending experience before a new action')
        o = world.observe_batch([agent])[0]
        state['counter'] += 1
        ident = f'dev-{agent}-{state["counter"]}'
        request = dict(schema_version=1, run_id=o['run_id'], request_id=ident, agent_id=agent,
            observation_version=o['observation_version'], action_type=action, target_ids=list(targets),
            parameters=parameters or {}, requested_duration=duration)
        # Native boundary still validates the complete request on submission.
        pending = {'request': request, 'before': o, 'learn_food': learn_food,
                   'prediction': prediction, 'status': 'reserved', 'update_memory': update_memory}
        _put(db, 'development_people', agent, state)
        _put(db, 'development_pending', agent, pending)
        db.commit()
        if fault:
            fault('after_reservation')
        return reconcile(path, agent, fault=fault)


def reconcile(path, agent, fault=None):
    with Lease(path):
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute('BEGIN')
            _person(db, agent, agent)
            if not db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone():
                return None
            pending = _read(db, 'development_pending', agent, 'agent')
            req = pending['request']
            rows = db.execute("SELECT request FROM decisions WHERE json_extract(request,'$.request_id')=? AND json_extract(request,'$.agent_id')=?",
                              (req['request_id'], agent)).fetchall()
            if rows and any(json.loads(row[0]) != req for row in rows):
                raise ValueError('native request identity conflict')
        if not rows:
            o = own_observation(path, agent)
            if o['observation_version'] != req['observation_version']:
                raise ValueError('unsubmitted intent at changed head; explicit recovery required')
            storage.advance(path, max(1, math.ceil(req['requested_duration'] / o['dt_s'])),
                            [(int(o['tick']), req)])
        else:
            # A crash may leave a submitted native request in flight. Never replay it.
            for _ in range(61):
                o = own_observation(path, agent)
                receipt = next((r for r in o['recent_action_results'] if r['request_id'] == req['request_id']), None)
                if receipt and receipt['status'] in ('completed', 'failed', 'rejected'):
                    break
                if not receipt or not o['own_state']['busy']:
                    raise ValueError('missing native receipt; outcome is unknown')
                storage.advance(path, 1)
            else:
                raise ValueError('native reconciliation exceeded action bound')
        if fault:
            fault('after_native_commit')
        o = own_observation(path, agent)
        receipt = next((r for r in o['recent_action_results'] if r['request_id'] == req['request_id']), None)
        if not receipt or receipt['status'] not in ('completed', 'failed', 'rejected'):
            raise ValueError('terminal own receipt unavailable')
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent, agent)
            ident = req['request_id']
            before = pending['before']
            target = next((e for e in before['visible_entities'] if e['entity_id'] in req['target_ids']), None)
            gain = int(o['own_state']['inventory_ug'].get('food', 0)) - int(before['own_state']['inventory_ug'].get('food', 0))
            value = {'mechanism': MECHANISM, 'run_id': o['run_id'], 'agent': agent,
                'request': req, 'before': before, 'after': o, 'receipt': receipt,
                'native_events': _source_events(db, path, receipt['event_refs']),
                'prediction': pending['prediction'], 'food_gain_ug': gain,
                'goal_success': receipt['status'] == 'completed' and gain > 0,
                'outcome_category': receipt['error_code'] or ('food_acquired' if gain > 0 else 'completed_without_food'),
                'learned': bool(pending['learn_food']), 'update_version': state['version'] + 1}
            _record(db, ident, agent, 'experience', value)
            if target and req['action_type'] == 'gather' and pending['update_memory']:
                key = sensory(target, before['own_state'])
                for table, index in (('objects', target['entity_id']), ('associations', key)):
                    if table == 'associations' and not pending['learn_food']:
                        continue
                    a = state[table].setdefault(index, {'n': 0, 'successes': 0, 'evidence': []})
                    a['n'] += 1
                    a['successes'] += int(value['goal_success'])
                    a['evidence'] = (a['evidence'] + [ident])[-16:]
            state['experiences'] += 1
            state['version'] += 1
            _put(db, 'development_people', agent, state)
            db.execute('DELETE FROM development_pending WHERE agent=?', (agent,))
            if fault:
                fault('before_update_commit')
            db.commit()
            if fault:
                fault('after_update_commit')
        return value


def audit(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        storage._head(db)
        meta = _meta(db)
        people = {a: _person(db, a, a) for a, in db.execute('SELECT agent FROM development_people')}
        if set(people) != set(meta['people']):
            raise ValueError('developmental cohort identity missing')
        counts = {}
        experiences = {}
        for ident, agent, kind, payload, checksum in db.execute('SELECT * FROM development_records ORDER BY id'):
            if hashlib.sha256(payload.encode()).hexdigest() != checksum:
                raise ValueError('developmental evidence checksum mismatch')
            value = json.loads(payload)
            if value['agent'] != agent or value['run_id'] != meta['run_id']:
                raise ValueError('developmental evidence identity mismatch')
            if kind == 'experience' and _source_events(db, path, value['receipt']['event_refs']) != value['native_events']:
                raise ValueError('native source proof mismatch')
            if kind == 'experience':
                experiences[agent] = experiences.get(agent, 0) + 1
            counts[agent] = counts.get(agent, 0) + 1
        if any(n > QUOTA for n in counts.values()):
            raise ValueError('developmental evidence quota exceeded')
        if any(s['experiences'] != experiences.get(a, 0) for a, s in people.items()):
            raise ValueError('developmental experience history missing')
        for a, in db.execute('SELECT agent FROM development_pending'):
            _read(db, 'development_pending', a, 'agent')
        return {'meta': meta, 'people': people, 'record_counts': counts,
                'pending': db.execute('SELECT COUNT(*) FROM development_pending').fetchone()[0],
                'operator_only': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('init', 'status', 'reconcile', 'choose', 'archive'))
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--seed', type=int, default=41)
    p.add_argument('--agent', default='agent-1')
    p.add_argument('--profile', choices=('novice-affordance',), default='novice-affordance')
    p.add_argument('--targets', nargs='*', default=[])
    args = p.parse_args()
    if args.command == 'init':
        result = initialize(args.db, seed=args.seed, profile=args.profile)
    elif args.command == 'status':
        result = audit(args.db)
    elif args.command == 'choose':
        result = choose(args.db, args.agent, args.targets)
    elif args.command == 'archive':
        result = archive(args.db)
    else:
        result = reconcile(args.db, args.agent)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
