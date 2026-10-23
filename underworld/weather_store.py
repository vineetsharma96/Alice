"""Separate transactional weather saves and replay journal. No historical schema edits."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from .lease import Lease
from .weather_runtime import climate, load


def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def connect(path, readonly=True):
    path = Path(path).resolve()
    db = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize(path, seed=53, population=4, configuration=None, guided=False, **kwargs):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError('Weather initialization requires a NEW path; never reset a life.')
    w = load().World(seed=seed, population=population, width=32, height=32, dt=.25,
                     scripted=False, bodies=True, run_id=str(uuid.uuid4()), guided=guided, **kwargs)
    w.configure_climate(configuration if configuration is not None else climate())
    checkpoint = w.checkpoint()
    # Exclusive creation prevents another initializer from replacing an existing world.
    with path.open('xb'):
        pass
    try:
        with Lease(path), closing(sqlite3.connect(path, isolation_level=None)) as db:
            db.executescript('''
                CREATE TABLE weather_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE weather_head(id INTEGER PRIMARY KEY CHECK(id=1),state TEXT NOT NULL,hash TEXT NOT NULL,policy TEXT NOT NULL,policy_hash TEXT NOT NULL);
                CREATE TABLE weather_operations(seq INTEGER PRIMARY KEY,command TEXT NOT NULL,before_hash TEXT NOT NULL,after_hash TEXT NOT NULL,result TEXT NOT NULL);
            ''')
            db.execute('BEGIN IMMEDIATE')
            meta = dict(format='ALICE-WEATHER-2', build_id=load().build_id,
                        policy_source=digest((Path(__file__).parent/'weather_policy.py').read_text(encoding='utf8')),
                        run_id=w.snapshot()['run_id'], initial=checkpoint, initial_hash=digest(checkpoint))
            db.executemany('INSERT INTO weather_meta VALUES(?,?)', meta.items())
            db.execute('INSERT INTO weather_head VALUES(1,?,?,?,?)', (checkpoint, digest(checkpoint), '{}', digest('{}')))
            db.commit()
    except BaseException:
        # Keep an explicit failed-initialization file for inspection; do not auto-reset it.
        raise
    return inspect(path)


def head(db):
    meta = dict(db.execute('SELECT key,value FROM weather_meta'))
    if meta['format'] != 'ALICE-WEATHER-2' or meta['build_id'] != load().build_id or meta['policy_source'] != digest((Path(__file__).parent/'weather_policy.py').read_text(encoding='utf8')):
        raise ValueError('Weather source/build mismatch: use matching runtime; no implicit migration.')
    state, checksum, policy, policy_hash = db.execute('SELECT state,hash,policy,policy_hash FROM weather_head WHERE id=1').fetchone()
    if digest(state) != checksum or digest(policy) != policy_hash:
        raise ValueError('Weather checkpoint checksum mismatch')
    return load().World.restore(state, meta['run_id']), meta, json.loads(policy)


def inspect(path):
    with closing(connect(path)) as db:
        w, _, policy = head(db)
        return dict(snapshot=w.snapshot(), climate=w.weather_snapshot(), policy=policy,
                    state_hash=digest(w.checkpoint()), operation_count=db.execute('SELECT COUNT(*) FROM weather_operations').fetchone()[0])


def observe(path, agent):
    with closing(connect(path)) as db:
        w, _, _ = head(db)
        return w.observe_batch([agent])[0]


def apply(w, command, policies=None):
    if command['kind'] == 'step':
        ticks = command['ticks']
        if type(ticks) is not int or not 0 <= ticks <= 10000:
            raise ValueError('Weather step requires 0..10000 integer ticks')
        return w.step(ticks)
    if command['kind'] == 'submit':
        return w.submit(command['request'], command['principal'])
    if command['kind'] == 'policy':
        from .weather_policy import advance
        return advance(w, policies, command['agent'], command.get('mode','weather'), command.get('assignment'))
    if command['kind'] == 'cohort':
        from .weather_policy import advance
        actors=sorted(e['entity_id'] for e in w.snapshot()['entities'] if e['kind']=='actor')
        schedule=policies.setdefault('_scheduler',dict(cursor=0))
        agent=actors[schedule['cursor']%len(actors)]
        result=advance(w,policies,agent,command.get('mode','weather'))
        schedule['cursor']+=1
        return result
    if command['kind'] == 'force':
        return w.force_weather(command['parameters'], 'operator')
    raise ValueError('Unknown weather journal command')


def commit(path, command):
    with Lease(path), closing(connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        w, _, policy = head(db)
        if db.execute('SELECT COUNT(*) FROM weather_operations').fetchone()[0] >= 25000:
            raise ValueError('Explicit weather journal budget reached; do not reset this life')
        before = digest(w.checkpoint())
        result = apply(w, command, policy)
        w.check_invariants()
        state = w.checkpoint()
        after = digest(state)
        db.execute('INSERT INTO weather_operations(command,before_hash,after_hash,result) VALUES(?,?,?,?)',
                   (dumps(command), before, after, dumps(result)))
        db.execute('UPDATE weather_head SET state=?,hash=?,policy=?,policy_hash=? WHERE id=1', (state, after, dumps(policy), digest(dumps(policy))))
        db.commit()
        return result


def replay(path):
    with closing(connect(path)) as db:
        final, meta, final_policy = head(db)
        if digest(meta['initial']) != meta['initial_hash']:
            raise ValueError('Initial weather state checksum mismatch')
        w = load().World.restore(meta['initial'], meta['run_id'])
        count = 0; policies = {}
        for command, before, after, result in db.execute('SELECT command,before_hash,after_hash,result FROM weather_operations ORDER BY seq'):
            if digest(w.checkpoint()) != before:
                raise ValueError('Weather journal chain mismatch')
            actual = apply(w, json.loads(command), policies)
            if dumps(actual) != result or digest(w.checkpoint()) != after:
                raise ValueError('Weather native replay mismatch')
            count += 1
        if w.checkpoint() != final.checkpoint() or dumps(policies) != dumps(final_policy):
            raise ValueError('Weather final replay mismatch')
        return dict(replay_matches=True, operations=count, state_hash=digest(w.checkpoint()))


def save(path, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Refuse overwriting a weather backup')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Lease(path), closing(connect(path)) as source:
        with destination.open('xb'):
            pass
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
    return inspect(destination)
