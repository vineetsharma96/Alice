"""Phase-2 ALICE-LIFE-2 private memory persistence.

Phase 2 builds on a Phase-1 destination.  It stores explicitly supplied
private memory records with durable source references, and represents
corrections as append-only status events rather than rewriting the original
memory payload.  Native weather/life state and Phase-1 records remain
authoritative and untouched.
"""

from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from . import life_contracts as contracts
from . import life_phase1 as phase1
from . import weather_store as weather
from .lease import Lease


PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-2'
VERSION = 1
MAX_MEMORIES = 25000
TABLES = {'phase2_meta', 'phase2_memories', 'phase2_memory_events', 'phase2_operations'}


def _dumps(value):
    return weather.dumps(value)


def _hash_text(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ensure_new_destination(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Phase-2 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _has_tables(path, names):
    with closing(sqlite3.connect(Path(path).resolve())) as db:
        found = {row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN (%s)" %
            ','.join('?' for _ in names), tuple(names))}
    return found == set(names)


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase2_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-2 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-2 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-2 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase2_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase2_meta(
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase2_memories(
            memory_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            native_tick INTEGER NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE INDEX phase2_memory_agent_tick
            ON phase2_memories(agent_id, native_tick, memory_id);
        CREATE TABLE phase2_memory_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            memory_id TEXT NOT NULL,
            event_kind TEXT NOT NULL,
            supersedes TEXT,
            native_tick INTEGER NOT NULL,
            result TEXT NOT NULL
        );
        CREATE TABLE phase2_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            agent_id TEXT,
            native_state_hash TEXT NOT NULL,
            memory_ids TEXT NOT NULL,
            result TEXT NOT NULL
        );
    ''')


def _source_refs(db, refs):
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError('memory source_refs must be a non-empty list of strings')
    known = set()
    for observation_id, payload in db.execute('SELECT observation_id,payload FROM phase1_observations'):
        known.add(observation_id)
        known.update(json.loads(payload).get('source_event_ids', []))
    missing = [ref for ref in refs if ref not in known]
    if missing:
        raise ValueError('memory source reference is not a Phase-1 observation reference')
    return list(dict.fromkeys(refs))


def _stored_memory(db, memory_id):
    row = db.execute('SELECT payload,checksum FROM phase2_memories WHERE memory_id=?', (memory_id,)).fetchone()
    if row is None:
        raise ValueError('unknown Phase-2 memory')
    payload, stored_checksum = row
    record = contracts.verify(json.loads(payload))
    if record['memory_id'] != memory_id or record['checksum'] != stored_checksum:
        raise ValueError('Phase-2 memory row mismatch')
    return record


def _event_statuses(db):
    statuses = {}
    for event_id, memory_id, event_kind, supersedes, native_tick, result in db.execute(
            'SELECT event_id,memory_id,event_kind,supersedes,native_tick,result FROM phase2_memory_events ORDER BY seq'):
        if event_kind not in ('created', 'superseded', 'invalidated'):
            raise ValueError('unknown Phase-2 memory event')
        if event_kind == 'created':
            if memory_id in statuses:
                raise ValueError('duplicate Phase-2 memory creation')
            statuses[memory_id] = {'effective_validity': 'active', 'events': [event_id]}
        else:
            if memory_id not in statuses:
                raise ValueError('Phase-2 status event precedes memory creation')
            if event_kind == 'superseded':
                if not supersedes or supersedes != memory_id:
                    raise ValueError('invalid Phase-2 supersession event')
                statuses[memory_id]['effective_validity'] = 'superseded'
            else:
                if supersedes is not None:
                    raise ValueError('invalid Phase-2 invalidation event')
                statuses[memory_id]['effective_validity'] = 'invalidated'
            statuses[memory_id]['events'].append(event_id)
        json.loads(result)
        if not isinstance(native_tick, int) or native_tick < 0 or not event_id:
            raise ValueError('invalid Phase-2 memory event envelope')
    return statuses


def _insert_operation(db, operation_id, kind, agent_id, native_hash, memory_ids, result):
    db.execute(
        'INSERT INTO phase2_operations(operation_id,kind,agent_id,native_state_hash,memory_ids,result) VALUES(?,?,?,?,?,?)',
        (operation_id, kind, agent_id, native_hash, _dumps(memory_ids), _dumps(result)))


def attach(source, destination):
    """Create a new Phase-2 copy from a Phase-1 destination."""
    source = Path(source).resolve()
    destination = _ensure_new_destination(destination)
    if not _has_tables(source, phase1.TABLES):
        raise ValueError('Phase-2 attach requires a Phase-1 destination')
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-2 records; use save for a backup')
    source_hash = _file_hash(source)
    weather.save(source, destination)
    try:
        if _file_hash(source) != source_hash:
            raise ValueError('Source changed during Phase-2 attach')
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            phase1_meta = phase1._meta(db)
            world, _, _, _ = phase1.life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            meta = {
                'schema': SCHEMA,
                'profile': PROFILE,
                'version': VERSION,
                'run_id': phase1_meta['run_id'],
                'actors': list(phase1_meta['actors']),
                'source_db_sha256': source_hash,
                'source_native_state_hash': native_hash,
                'phase1_source_hash': source_hash,
                'operation_quota': MAX_MEMORIES,
            }
            _create_tables(db)
            payload = _dumps(meta)
            db.execute('INSERT INTO phase2_meta VALUES(1,?,?)', (payload, _hash_text(payload)))
            db.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return inspect(destination)


def write_memory(path, *, agent_id, memory_id, memory_kind, content, source_refs,
                 confidence=0.0, salience=0.0, native_tick=None,
                 observation_version=None, provenance='authored',
                 validity='active', supersedes=None, operation_id=None):
    """Append one explicitly supplied private memory and its source links."""
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
        snapshot = world.snapshot()
        native_hash = weather.digest(world.checkpoint())
        actors = set(meta['actors'])
        if agent_id not in actors:
            raise ValueError('memory owner is not enrolled in Phase 2')
        tick = int(snapshot['tick']) if native_tick is None else native_tick
        version = tick if observation_version is None else observation_version
        if type(tick) is not int or tick < 0 or tick > int(snapshot['tick']):
            raise ValueError('memory native_tick must be current or historical native time')
        if type(version) is not int or version < 0 or version > tick:
            raise ValueError('memory observation_version must be bounded by native_tick')
        _source_refs(db, source_refs)
        if db.execute('SELECT COUNT(*) FROM phase2_memories').fetchone()[0] >= MAX_MEMORIES:
            raise ValueError('Phase-2 memory quota reached; do not reset this life')
        if db.execute('SELECT 1 FROM phase2_memories WHERE memory_id=?', (memory_id,)).fetchone():
            raise ValueError('Phase-2 memory_id already exists')
        if supersedes is not None:
            prior = _stored_memory(db, supersedes)
            statuses = _event_statuses(db)
            if statuses[supersedes]['effective_validity'] != 'active':
                raise ValueError('only an active memory can be superseded')
            if prior['agent_id'] != agent_id:
                raise ValueError('memory corrections must retain the original owner')
        record = contracts.memory(
            agent_id=agent_id, run_id=meta['run_id'], native_tick=tick,
            observation_version=version, memory_id=memory_id, memory_kind=memory_kind,
            content=content, source_refs=_source_refs(db, source_refs), confidence=confidence,
            salience=salience, validity=validity, supersedes=supersedes,
            provenance=provenance, privacy_scope='private', branch_id='main')
        payload = _dumps(record)
        db.execute('INSERT INTO phase2_memories VALUES(?,?,?,?,?)',
                   (memory_id, agent_id, tick, payload, record['checksum']))
        event_id = f'created:{memory_id}'
        db.execute('INSERT INTO phase2_memory_events(event_id,memory_id,event_kind,supersedes,native_tick,result) VALUES(?,?,?,?,?,?)',
                   (event_id, memory_id, 'created', None, tick, _dumps({'checksum': record['checksum']})))
        if supersedes is not None:
            status_event = f'supersede:{supersedes}:{memory_id}'
            db.execute('INSERT INTO phase2_memory_events(event_id,memory_id,event_kind,supersedes,native_tick,result) VALUES(?,?,?,?,?,?)',
                       (status_event, supersedes, 'superseded', supersedes, tick,
                        _dumps({'replacement': memory_id})))
        op = operation_id or f'memory:{memory_id}'
        _insert_operation(db, op, 'write_memory', agent_id, native_hash, [memory_id] + ([supersedes] if supersedes else []),
                          {'memory_checksum': record['checksum'], 'supersedes': supersedes})
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = int(snapshot['tick'])
        _write_meta(db, meta)
        db.commit()
    return memory(path, memory_id)


def invalidate(path, memory_id, *, operation_id=None):
    """Append an invalidation event without rewriting the memory payload."""
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        prior = _stored_memory(db, memory_id)
        statuses = _event_statuses(db)
        if statuses[memory_id]['effective_validity'] != 'active':
            raise ValueError('only an active memory can be invalidated')
        world, _, _, _ = phase1.life_store.head(db)
        native_hash = weather.digest(world.checkpoint())
        tick = int(world.snapshot()['tick'])
        event_id = f'invalidate:{memory_id}'
        db.execute('INSERT INTO phase2_memory_events(event_id,memory_id,event_kind,supersedes,native_tick,result) VALUES(?,?,?,?,?,?)',
                   (event_id, memory_id, 'invalidated', None, tick, _dumps({'reason': 'explicit invalidation'})))
        op = operation_id or event_id
        _insert_operation(db, op, 'invalidate_memory', prior['agent_id'], native_hash, [memory_id],
                          {'memory_checksum': prior['checksum']})
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = tick
        _write_meta(db, meta)
        db.commit()
    return memory(path, memory_id)


def memory(path, memory_id):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        record = _stored_memory(db, memory_id)
        status = _event_statuses(db)[memory_id]
        return {'record': record, 'effective_validity': status['effective_validity'], 'event_ids': list(status['events'])}


def memories(path, *, agent_id=None, active_only=False):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        statuses = _event_statuses(db)
        query = 'SELECT memory_id FROM phase2_memories ORDER BY native_tick,memory_id'
        ids = [row[0] for row in db.execute(query)]
        result = []
        for memory_id in ids:
            item = {'record': _stored_memory(db, memory_id),
                    'effective_validity': statuses[memory_id]['effective_validity'],
                    'event_ids': list(statuses[memory_id]['events'])}
            if agent_id is not None and item['record']['agent_id'] != agent_id:
                continue
            if active_only and item['effective_validity'] != 'active':
                continue
            result.append(item)
        if agent_id is not None and agent_id not in set(meta['actors']):
            raise ValueError('memory owner is not enrolled in Phase 2')
        return result


def inspect(path):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
        snapshot = world.snapshot()
        statuses = _event_statuses(db)
        return {
            'schema': meta['schema'], 'profile': meta['profile'], 'version': meta['version'],
            'run_id': meta['run_id'], 'actors': list(meta['actors']),
            'native_tick': int(snapshot['tick']), 'native_simulated_time_s': float(snapshot['simulated_time_s']),
            'native_state_hash': weather.digest(world.checkpoint()),
            'source_db_sha256': meta['source_db_sha256'],
            'phase1_source_hash': meta['phase1_source_hash'],
            'memory_count': db.execute('SELECT COUNT(*) FROM phase2_memories').fetchone()[0],
            'active_memory_count': sum(1 for value in statuses.values() if value['effective_validity'] == 'active'),
            'operation_count': db.execute('SELECT COUNT(*) FROM phase2_operations').fetchone()[0],
            'event_count': db.execute('SELECT COUNT(*) FROM phase2_memory_events').fetchone()[0],
        }


def replay(path):
    """Verify Phase-1 plus Phase-2 records and append-only correction events."""
    phase1_result = phase1.replay(path)
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        statuses = _event_statuses(db)
        memory_count = 0
        for memory_id, agent_id, payload, stored_checksum in db.execute(
                'SELECT memory_id,agent_id,payload,checksum FROM phase2_memories ORDER BY native_tick,memory_id'):
            record = contracts.verify(json.loads(payload))
            if record['memory_id'] != memory_id or record['agent_id'] != agent_id or record['checksum'] != stored_checksum:
                raise ValueError('Phase-2 memory row mismatch')
            if record['run_id'] != meta['run_id'] or record['privacy_scope'] != 'private':
                raise ValueError('Phase-2 memory ownership/privacy mismatch')
            _source_refs(db, record['source_event_ids'])
            if memory_id not in statuses:
                raise ValueError('Phase-2 memory has no lifecycle event')
            if record['supersedes'] is not None:
                prior = db.execute('SELECT 1 FROM phase2_memories WHERE memory_id=?', (record['supersedes'],)).fetchone()
                if prior is None:
                    raise ValueError('Phase-2 memory supersedes an unknown memory')
            memory_count += 1
        operation_count = 0
        for operation_id, kind, agent_id, native_hash, memory_ids, result in db.execute(
                'SELECT operation_id,kind,agent_id,native_state_hash,memory_ids,result FROM phase2_operations ORDER BY seq'):
            if not operation_id or kind not in ('write_memory', 'invalidate_memory'):
                raise ValueError('Phase-2 operation mismatch')
            if agent_id is not None and agent_id not in meta['actors']:
                raise ValueError('Phase-2 operation owner mismatch')
            if not isinstance(native_hash, str) or len(native_hash) != 64:
                raise ValueError('Phase-2 operation native hash is invalid')
            if not isinstance(json.loads(memory_ids), list):
                raise ValueError('Phase-2 operation memory_ids is invalid')
            json.loads(result)
            operation_count += 1
        return dict(phase1_result, phase2_verified=True, memories=memory_count, phase2_operations=operation_count,
                    phase2_schema=meta['schema'])


def save(path, destination):
    destination = _ensure_new_destination(destination)
    weather.save(path, destination)
    return inspect(destination)
