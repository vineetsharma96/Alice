"""Phase-6 ALICE-LIFE-2 social and cultural provenance persistence.

Phase 6 adds an append-only ledger for observed interactions and explicitly
authored cultural artifacts.  It is a persistence boundary only: it does not
force cooperation, create native actions, infer trust, or expose another
inhabitant's private state without a recorded access event.
"""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from . import life_contracts as contracts
from . import life_phase1 as phase1
from . import life_phase5 as phase5
from . import weather_store as weather
from .lease import Lease

PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-6'
VERSION = 1
MAX_EVENTS = 25000
MAX_ARTIFACTS = 10000
EVENT_KINDS = frozenset({'speech', 'gift', 'offer', 'response', 'shared_task', 'artifact_read', 'departure'})
ARTIFACT_KINDS = frozenset({'procedure', 'book', 'report', 'tool'})
TABLES = {'phase6_meta', 'phase6_events', 'phase6_artifacts', 'phase6_operations'}


def _dumps(value):
    return weather.dumps(value)


def _hash_text(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _has_tables(path, names):
    with closing(sqlite3.connect(Path(path).resolve())) as db:
        found = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (%s)" %
            ','.join('?' for _ in names), tuple(names))}
    return found == set(names)


def _new(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Phase-6 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase6_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-6 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-6 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-6 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase6_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase6_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1), payload TEXT NOT NULL, checksum TEXT NOT NULL);
        CREATE TABLE phase6_events(
            event_id TEXT PRIMARY KEY, event_kind TEXT NOT NULL, actor_id TEXT NOT NULL,
            other_actor_id TEXT, native_tick INTEGER NOT NULL, source_refs TEXT NOT NULL,
            payload TEXT NOT NULL, checksum TEXT NOT NULL);
        CREATE INDEX phase6_event_actor_tick ON phase6_events(actor_id, native_tick, event_id);
        CREATE TABLE phase6_artifacts(
            artifact_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, artifact_kind TEXT NOT NULL,
            native_tick INTEGER NOT NULL, source_refs TEXT NOT NULL, payload TEXT NOT NULL,
            checksum TEXT NOT NULL);
        CREATE TABLE phase6_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL, actor_id TEXT NOT NULL, native_state_hash TEXT NOT NULL,
            record_ids TEXT NOT NULL, result TEXT NOT NULL);
    ''')


def _actor(meta, agent_id):
    if agent_id not in set(meta['actors']):
        raise ValueError('Phase-6 actor is not enrolled')


def _refs(db, refs):
    if not isinstance(refs, list) or not refs or any(type(ref) is not str or not ref for ref in refs):
        raise ValueError('Phase-6 source_refs must be a non-empty list of strings')
    known = set()
    for observation_id, payload in db.execute('SELECT observation_id,payload FROM phase1_observations'):
        known.add(observation_id)
        known.update(json.loads(payload).get('source_event_ids', []))
    missing = [ref for ref in refs if ref not in known]
    if missing:
        raise ValueError('Phase-6 source reference is not a Phase-1 observation reference')
    return list(dict.fromkeys(refs))


def _record_checksum(value):
    return _hash_text(_dumps(value))


def attach(source, destination):
    source = Path(source).resolve()
    destination = _new(destination)
    if not _has_tables(source, phase5.TABLES):
        raise ValueError('Phase-6 attach requires a Phase-5 destination')
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-6 records; use save for a backup')
    source_hash = _file_hash(source)
    weather.save(source, destination)
    try:
        if _file_hash(source) != source_hash:
            raise ValueError('Source changed during Phase-6 attach')
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            upstream = phase5._meta(db)
            world, _, _, _ = phase1.life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            meta = {'schema': SCHEMA, 'profile': PROFILE, 'version': VERSION,
                    'run_id': upstream['run_id'], 'actors': list(upstream['actors']),
                    'source_db_sha256': source_hash, 'phase5_source_hash': source_hash,
                    'source_native_state_hash': native_hash, 'event_quota': MAX_EVENTS,
                    'artifact_quota': MAX_ARTIFACTS}
            _create_tables(db)
            text = _dumps(meta)
            db.execute('INSERT INTO phase6_meta VALUES(1,?,?)', (text, _hash_text(text)))
            db.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return inspect(destination)


def _head(db):
    meta = _meta(db)
    world, _, _, _ = phase1.life_store.head(db)
    return meta, world, weather.digest(world.checkpoint()), int(world.snapshot()['tick'])


def record_event(path, *, event_id, event_kind, actor_id, other_actor_id=None,
                 payload=None, source_refs=None, native_tick=None, operation_id=None):
    if event_kind not in EVENT_KINDS:
        raise ValueError('unknown Phase-6 event kind')
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta, world, native_hash, current_tick = _head(db)
        _actor(meta, actor_id)
        if other_actor_id is not None:
            _actor(meta, other_actor_id)
            if other_actor_id == actor_id:
                raise ValueError('Phase-6 event participants must differ')
        tick = current_tick if native_tick is None else native_tick
        if type(tick) is not int or tick < 0 or tick > current_tick:
            raise ValueError('Phase-6 event native_tick is invalid')
        refs = _refs(db, source_refs or [])
        if not isinstance(payload or {}, dict):
            raise ValueError('Phase-6 event payload must be a mapping')
        if db.execute('SELECT 1 FROM phase6_events WHERE event_id=?', (event_id,)).fetchone():
            raise ValueError('Phase-6 event_id already exists')
        if db.execute('SELECT COUNT(*) FROM phase6_events').fetchone()[0] >= MAX_EVENTS:
            raise ValueError('Phase-6 event quota reached')
        value = {'profile': PROFILE, 'schema': SCHEMA, 'version': VERSION,
                 'event_id': event_id, 'event_kind': event_kind, 'actor_id': actor_id,
                 'other_actor_id': other_actor_id, 'run_id': meta['run_id'],
                 'native_tick': tick, 'source_refs': refs, 'payload': payload,
                 'privacy_scope': 'private'}
        checksum = _record_checksum(value)
        db.execute('INSERT INTO phase6_events VALUES(?,?,?,?,?,?,?,?)',
                   (event_id, event_kind, actor_id, other_actor_id, tick, _dumps(refs), _dumps(value), checksum))
        op = operation_id or f'event:{event_id}'
        db.execute('INSERT INTO phase6_operations(kind,operation_id,actor_id,native_state_hash,record_ids,result) VALUES(?,?,?,?,?,?)',
                   ('event', op, actor_id, native_hash, _dumps([event_id]), _dumps({'checksum': checksum})))
        meta['last_native_tick'] = current_tick
        meta['last_native_state_hash'] = native_hash
        _write_meta(db, meta)
        db.commit()
    return event(path, event_id)


def event(path, event_id):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        row = db.execute('SELECT payload,checksum FROM phase6_events WHERE event_id=?', (event_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-6 event')
        value = json.loads(row[0])
        if _record_checksum(value) != row[1]:
            raise ValueError('Phase-6 event checksum mismatch')
        return value


def write_artifact(path, *, artifact_id, owner_id, artifact_kind, content, source_refs,
                   native_tick=None, operation_id=None):
    if artifact_kind not in ARTIFACT_KINDS:
        raise ValueError('unknown Phase-6 artifact kind')
    if not isinstance(content, dict):
        raise ValueError('Phase-6 artifact content must be a mapping')
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta, world, native_hash, current_tick = _head(db)
        _actor(meta, owner_id)
        tick = current_tick if native_tick is None else native_tick
        if type(tick) is not int or tick < 0 or tick > current_tick:
            raise ValueError('Phase-6 artifact native_tick is invalid')
        refs = _refs(db, source_refs)
        if db.execute('SELECT 1 FROM phase6_artifacts WHERE artifact_id=?', (artifact_id,)).fetchone():
            raise ValueError('Phase-6 artifact_id already exists')
        if db.execute('SELECT COUNT(*) FROM phase6_artifacts').fetchone()[0] >= MAX_ARTIFACTS:
            raise ValueError('Phase-6 artifact quota reached')
        value = {'profile': PROFILE, 'schema': SCHEMA, 'version': VERSION,
                 'artifact_id': artifact_id, 'owner_id': owner_id, 'artifact_kind': artifact_kind,
                 'run_id': meta['run_id'], 'native_tick': tick, 'source_refs': refs,
                 'content': content, 'access': {'owner_id': owner_id, 'readers': []},
                 'privacy_scope': 'private'}
        checksum = _record_checksum(value)
        db.execute('INSERT INTO phase6_artifacts VALUES(?,?,?,?,?,?,?)',
                   (artifact_id, owner_id, artifact_kind, tick, _dumps(refs), _dumps(value), checksum))
        op = operation_id or f'artifact:{artifact_id}'
        db.execute('INSERT INTO phase6_operations(kind,operation_id,actor_id,native_state_hash,record_ids,result) VALUES(?,?,?,?,?,?)',
                   ('artifact', op, owner_id, native_hash, _dumps([artifact_id]), _dumps({'checksum': checksum})))
        meta['last_native_tick'] = current_tick
        meta['last_native_state_hash'] = native_hash
        _write_meta(db, meta)
        db.commit()
    return artifact(path, artifact_id, owner_id)


def artifact(path, artifact_id, reader_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        row = db.execute('SELECT payload,checksum FROM phase6_artifacts WHERE artifact_id=?', (artifact_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-6 artifact')
        value = json.loads(row[0])
        if _record_checksum(value) != row[1]:
            raise ValueError('Phase-6 artifact checksum mismatch')
        if reader_id is None:
            return {key: value[key] for key in value if key != 'content'}
        _actor(meta, reader_id)
        if reader_id != value['owner_id'] and reader_id not in value['access']['readers']:
            raise ValueError('Phase-6 artifact has not been accessed by this actor')
        return value


def read_artifact(path, *, artifact_id, reader_id, source_refs, operation_id=None):
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta, world, native_hash, current_tick = _head(db)
        _actor(meta, reader_id)
        row = db.execute('SELECT payload,checksum FROM phase6_artifacts WHERE artifact_id=?', (artifact_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-6 artifact')
        value = json.loads(row[0])
        if _record_checksum(value) != row[1]:
            raise ValueError('Phase-6 artifact checksum mismatch')
        _refs(db, source_refs)
        if reader_id not in value['access']['readers'] and reader_id != value['owner_id']:
            value['access']['readers'].append(reader_id)
            value['access']['readers'].sort()
            db.execute('UPDATE phase6_artifacts SET payload=?,checksum=? WHERE artifact_id=?',
                       (_dumps(value), _record_checksum(value), artifact_id))
        event_id = f'artifact-read:{artifact_id}:{reader_id}:{current_tick}'
        if not db.execute('SELECT 1 FROM phase6_events WHERE event_id=?', (event_id,)).fetchone():
            event_value = {'profile': PROFILE, 'schema': SCHEMA, 'version': VERSION,
                           'event_id': event_id, 'event_kind': 'artifact_read', 'actor_id': reader_id,
                           'other_actor_id': value['owner_id'], 'run_id': meta['run_id'],
                           'native_tick': current_tick, 'source_refs': list(dict.fromkeys(source_refs)),
                           'payload': {'artifact_id': artifact_id}, 'privacy_scope': 'private'}
            db.execute('INSERT INTO phase6_events VALUES(?,?,?,?,?,?,?,?)',
                       (event_id, 'artifact_read', reader_id, value['owner_id'], current_tick,
                        _dumps(event_value['source_refs']), _dumps(event_value), _record_checksum(event_value)))
        op = operation_id or f'read:{artifact_id}:{reader_id}:{current_tick}'
        db.execute('INSERT INTO phase6_operations(kind,operation_id,actor_id,native_state_hash,record_ids,result) VALUES(?,?,?,?,?,?)',
                   ('artifact_read', op, reader_id, native_hash, _dumps([artifact_id, event_id]), _dumps({'artifact_id': artifact_id})))
        _write_meta(db, meta)
        db.commit()
    return artifact(path, artifact_id, reader_id)


def events(path, *, actor_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        if actor_id is not None:
            _actor(meta, actor_id)
        query = 'SELECT payload,checksum FROM phase6_events'
        params = ()
        if actor_id is not None:
            query += ' WHERE actor_id=?'
            params = (actor_id,)
        query += ' ORDER BY native_tick,event_id'
        result = []
        for payload, checksum in db.execute(query, params):
            value = json.loads(payload)
            if _record_checksum(value) != checksum:
                raise ValueError('Phase-6 event checksum mismatch')
            result.append(value)
        return result


def artifacts(path, *, owner_id=None, reader_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        if owner_id is not None:
            _actor(meta, owner_id)
        if reader_id is not None:
            _actor(meta, reader_id)
        rows = db.execute('SELECT artifact_id,payload,checksum FROM phase6_artifacts ORDER BY native_tick,artifact_id')
        result = []
        for artifact_id, payload, checksum in rows:
            value = json.loads(payload)
            if _record_checksum(value) != checksum:
                raise ValueError('Phase-6 artifact checksum mismatch')
            if owner_id is not None and value['owner_id'] != owner_id:
                continue
            if reader_id is not None and reader_id not in value['access']['readers'] and reader_id != value['owner_id']:
                continue
            result.append({key: value[key] for key in value if key != 'content'})
        return result


def inspect(path):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta, world, native_hash, _ = _head(db)
        return {'schema': meta['schema'], 'profile': meta['profile'], 'version': meta['version'],
                'run_id': meta['run_id'], 'actors': list(meta['actors']),
                'native_tick': int(world.snapshot()['tick']), 'native_state_hash': native_hash,
                'source_db_sha256': meta['source_db_sha256'], 'phase5_source_hash': meta['phase5_source_hash'],
                'event_count': db.execute('SELECT COUNT(*) FROM phase6_events').fetchone()[0],
                'artifact_count': db.execute('SELECT COUNT(*) FROM phase6_artifacts').fetchone()[0],
                'operation_count': db.execute('SELECT COUNT(*) FROM phase6_operations').fetchone()[0]}


def replay(path):
    upstream = phase5.replay(path)
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        event_count = 0
        for event_id, payload, checksum in db.execute('SELECT event_id,payload,checksum FROM phase6_events ORDER BY native_tick,event_id'):
            value = json.loads(payload)
            if value['event_id'] != event_id or _record_checksum(value) != checksum:
                raise ValueError('Phase-6 event row mismatch')
            if value['run_id'] != meta['run_id'] or value['event_kind'] not in EVENT_KINDS:
                raise ValueError('Phase-6 event envelope mismatch')
            _refs(db, value['source_refs'])
            event_count += 1
        artifact_count = 0
        for artifact_id, payload, checksum in db.execute('SELECT artifact_id,payload,checksum FROM phase6_artifacts ORDER BY native_tick,artifact_id'):
            value = json.loads(payload)
            if value['artifact_id'] != artifact_id or _record_checksum(value) != checksum:
                raise ValueError('Phase-6 artifact row mismatch')
            if value['owner_id'] not in meta['actors'] or value['artifact_kind'] not in ARTIFACT_KINDS:
                raise ValueError('Phase-6 artifact envelope mismatch')
            _refs(db, value['source_refs'])
            if any(reader not in meta['actors'] for reader in value['access']['readers']):
                raise ValueError('Phase-6 artifact access owner mismatch')
            artifact_count += 1
        operations = 0
        for kind, operation_id, actor_id, native_hash, record_ids, result in db.execute(
                'SELECT kind,operation_id,actor_id,native_state_hash,record_ids,result FROM phase6_operations ORDER BY seq'):
            if kind not in ('event', 'artifact', 'artifact_read') or not operation_id or actor_id not in meta['actors']:
                raise ValueError('Phase-6 operation envelope mismatch')
            if not isinstance(native_hash, str) or len(native_hash) != 64 or not isinstance(json.loads(record_ids), list):
                raise ValueError('Phase-6 operation hash/records mismatch')
            json.loads(result)
            operations += 1
        return dict(upstream, phase6_verified=True, phase6_events=event_count,
                    phase6_artifacts=artifact_count, phase6_operations=operations,
                    phase6_schema=meta['schema'])


def save(path, destination):
    destination = _new(destination)
    weather.save(path, destination)
    return inspect(destination)
