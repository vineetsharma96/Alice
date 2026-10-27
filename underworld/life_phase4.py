"""Phase-4 ALICE-LIFE-2 private affect and mood trace persistence.

Phase 4 records the private affect state already present in the integrated-life
runtime.  It does not create a second affect engine, infer hidden causes, or
change native policy/action behaviour.  Native life state and Phase 3 body
records remain authoritative.
"""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from . import life_contracts as contracts
from . import life_phase1 as phase1
from . import life_phase2 as phase2
from . import life_phase3 as phase3
from . import weather_store as weather
from .lease import Lease


PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-4'
VERSION = 1
MAX_AFFECT_TRACES = 25000
TABLES = {'phase4_meta', 'phase4_affect_traces', 'phase4_operations'}


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


def _ensure_new_destination(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError('Phase-4 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase4_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-4 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-4 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-4 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase4_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase4_meta(
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase4_affect_traces(
            affect_trace_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            tick_before INTEGER NOT NULL,
            tick_after INTEGER NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE INDEX phase4_affect_agent_tick
            ON phase4_affect_traces(agent_id, tick_after, affect_trace_id);
        CREATE TABLE phase4_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            native_state_hash TEXT NOT NULL,
            affect_trace_ids TEXT NOT NULL,
            result TEXT NOT NULL
        );
    ''')


def _body_need_id(db, agent_id, tick):
    row = db.execute(
        'SELECT body_need_id FROM phase3_body_needs WHERE agent_id=? AND native_tick=? ORDER BY rowid DESC LIMIT 1',
        (agent_id, tick)).fetchone()
    if row is None:
        raise ValueError('affect trace requires a persisted Phase-3 body need at the same native tick')
    return row[0]


def _body_need_row(db, body_need_id):
    row = db.execute('SELECT payload,checksum FROM phase3_body_needs WHERE body_need_id=?', (body_need_id,)).fetchone()
    if row is None:
        raise ValueError('affect trace body source is missing')
    payload, checksum = row
    record = contracts.verify(json.loads(payload))
    if record['checksum'] != checksum or record['record_type'] != 'body_need':
        raise ValueError('affect trace body source row mismatch')
    return record


def _last_trace_tick(db, agent_id):
    row = db.execute(
        'SELECT tick_after FROM phase4_affect_traces WHERE agent_id=? ORDER BY tick_after DESC, rowid DESC LIMIT 1',
        (agent_id,)).fetchone()
    return int(row[0]) if row is not None else None


def _trace_record(person, agent_id, run_id, tick, body_need_id, previous_tick):
    last = person.get('last') if isinstance(person, dict) else None
    appraisal = last.get('appraisal', {}) if isinstance(last, dict) else {}
    explanation_status = 'recorded' if isinstance(last, dict) and appraisal else 'unavailable'
    life = person.get('life', {}) if isinstance(person, dict) else {}
    social = life.get('social', {}) if isinstance(life, dict) else {}
    social_changes = social.get('last_update', []) if isinstance(social, dict) else []
    if not isinstance(social_changes, list):
        social_changes = [social_changes]
    action_influence = life.get('last_decision', {}) if isinstance(life, dict) else {}
    if not isinstance(action_influence, dict):
        action_influence = {}
    memory = person.get('emotional_memory', {}) if isinstance(person, dict) else {}
    memory_refs = memory.get('entries', []) if isinstance(memory, dict) else []
    emotional_memory_refs = [entry.get('event') for entry in memory_refs
                             if isinstance(entry, dict) and isinstance(entry.get('event'), str)]
    return contracts.affect_trace(
        agent_id=agent_id, run_id=run_id,
        tick_before=tick if previous_tick is None else previous_tick,
        tick_after=tick, observation_version=tick,
        body_signals=person.get('body', {}) if isinstance(person, dict) else {},
        appraisal=appraisal,
        fast_affect=person.get('affect', {}) if isinstance(person, dict) else {},
        slow_mood=person.get('mood', {}) if isinstance(person, dict) else {},
        emotional_memory_refs=emotional_memory_refs,
        social_emotion_changes=social_changes,
        action_influence=action_influence,
        explanation_status=explanation_status,
        source_event_ids=[body_need_id], provenance='derived', privacy_scope='private', branch_id='main')


def _insert_operation(db, operation_id, kind, agent_id, native_hash, ids, result):
    db.execute(
        'INSERT INTO phase4_operations(operation_id,kind,agent_id,native_state_hash,affect_trace_ids,result) VALUES(?,?,?,?,?,?)',
        (operation_id, kind, agent_id, native_hash, _dumps(ids), _dumps(result)))


def attach(source, destination):
    """Create a new Phase-4 copy from a Phase-3 destination."""
    source = Path(source).resolve()
    destination = _ensure_new_destination(destination)
    if not _has_tables(source, phase3.TABLES):
        raise ValueError('Phase-4 attach requires a Phase-3 destination')
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-4 records; use save for a backup')
    source_hash = _file_hash(source)
    weather.save(source, destination)
    try:
        if _file_hash(source) != source_hash:
            raise ValueError('Source changed during Phase-4 attach')
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            phase3_meta = phase3._meta(db)
            world, _, people, _ = phase1.life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            meta = {
                'schema': SCHEMA, 'profile': PROFILE, 'version': VERSION,
                'run_id': phase3_meta['run_id'], 'actors': list(phase3_meta['actors']),
                'source_db_sha256': source_hash, 'phase3_source_hash': source_hash,
                'source_native_state_hash': native_hash, 'operation_quota': MAX_AFFECT_TRACES,
            }
            _create_tables(db)
            payload = _dumps(meta)
            db.execute('INSERT INTO phase4_meta VALUES(1,?,?)', (payload, _hash_text(payload)))
            db.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return capture(destination)


def capture(path, *, agents=None):
    """Persist one private affect trace per selected actor at the native head."""
    path = Path(path).resolve()
    with closing(weather.connect(path)) as db:
        meta = _meta(db)
    selected = list(meta['actors'] if agents is None else agents)
    if not selected or len(set(selected)) != len(selected) or any(agent not in set(meta['actors']) for agent in selected):
        raise ValueError('Phase-4 agents must be unique enrolled actors')
    # Keep the source chain complete without advancing native time.
    phase3.capture(path, agents=selected)
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        world, _, people, _ = phase1.life_store.head(db)
        snapshot = world.snapshot()
        tick = int(snapshot['tick'])
        native_hash = weather.digest(world.checkpoint())
        if db.execute('SELECT COUNT(*) FROM phase4_affect_traces').fetchone()[0] + len(selected) > MAX_AFFECT_TRACES:
            raise ValueError('Phase-4 affect-trace quota reached; do not reset this life')
        inserted = []
        for agent_id in selected:
            person = people.get(agent_id)
            if not isinstance(person, dict):
                raise ValueError('Phase-4 private affect state is missing')
            body_need_id = _body_need_id(db, agent_id, tick)
            _body_need_row(db, body_need_id)
            trace_id = f'affect:{agent_id}:{tick}:{native_hash[:16]}'
            prior = db.execute('SELECT payload,checksum FROM phase4_affect_traces WHERE affect_trace_id=?', (trace_id,)).fetchone()
            if prior is not None:
                payload, checksum = prior
                existing = contracts.verify(json.loads(payload))
                if existing['checksum'] != checksum:
                    raise ValueError('Phase-4 affect-trace row mismatch')
                continue
            previous_tick = _last_trace_tick(db, agent_id)
            record = _trace_record(person, agent_id, meta['run_id'], tick, body_need_id, previous_tick)
            payload = _dumps(record)
            db.execute('INSERT INTO phase4_affect_traces VALUES(?,?,?,?,?,?)',
                       (trace_id, agent_id, record['tick_before'], record['tick_after'], payload, record['checksum']))
            _insert_operation(db, trace_id, 'capture', agent_id, native_hash, [trace_id],
                              {'affect_trace_checksum': record['checksum'], 'body_need_id': body_need_id})
            inserted.append(trace_id)
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = tick
        _write_meta(db, meta)
        db.commit()
    return inspect(path) | {'captured_affect_trace_ids': inserted}


def affect_trace(path, affect_trace_id):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        row = db.execute('SELECT payload,checksum FROM phase4_affect_traces WHERE affect_trace_id=?', (affect_trace_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-4 affect trace')
        payload, checksum = row
        record = contracts.verify(json.loads(payload))
        if record['checksum'] != checksum:
            raise ValueError('Phase-4 affect-trace row mismatch')
        return record


def affect_traces(path, *, agent_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        if agent_id is not None and agent_id not in set(meta['actors']):
            raise ValueError('affect owner is not enrolled in Phase 4')
        query = 'SELECT payload,checksum FROM phase4_affect_traces'
        params = ()
        if agent_id is not None:
            query += ' WHERE agent_id=?'
            params = (agent_id,)
        query += ' ORDER BY tick_after,affect_trace_id'
        result = []
        for payload, checksum in db.execute(query, params):
            record = contracts.verify(json.loads(payload))
            if record['checksum'] != checksum:
                raise ValueError('Phase-4 affect-trace row mismatch')
            result.append(record)
        return result


def inspect(path):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
        snapshot = world.snapshot()
        return {
            'schema': meta['schema'], 'profile': meta['profile'], 'version': meta['version'],
            'run_id': meta['run_id'], 'actors': list(meta['actors']),
            'native_tick': int(snapshot['tick']), 'native_simulated_time_s': float(snapshot['simulated_time_s']),
            'native_state_hash': weather.digest(world.checkpoint()),
            'source_db_sha256': meta['source_db_sha256'], 'phase3_source_hash': meta['phase3_source_hash'],
            'affect_trace_count': db.execute('SELECT COUNT(*) FROM phase4_affect_traces').fetchone()[0],
            'operation_count': db.execute('SELECT COUNT(*) FROM phase4_operations').fetchone()[0],
        }


def replay(path):
    """Verify Phase 1-3 and affect traces against private body sources."""
    phase3_result = phase3.replay(path)
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        count = 0
        for trace_id, agent_id, payload, stored_checksum in db.execute(
                'SELECT affect_trace_id,agent_id,payload,checksum FROM phase4_affect_traces ORDER BY tick_after,affect_trace_id'):
            record = contracts.verify(json.loads(payload))
            if record['record_type'] != 'affect_trace' or record['agent_id'] != agent_id or record['checksum'] != stored_checksum:
                raise ValueError('Phase-4 affect-trace row mismatch')
            if record['run_id'] != meta['run_id'] or record['privacy_scope'] != 'private' or record['provenance'] != 'derived':
                raise ValueError('Phase-4 affect-trace ownership/privacy mismatch')
            if not trace_id.startswith(f'affect:{agent_id}:{record["tick_after"]}:'):
                raise ValueError('Phase-4 affect-trace identity mismatch')
            if record['tick_before'] > record['tick_after'] or not record['source_event_ids']:
                raise ValueError('Phase-4 affect-trace interval/source mismatch')
            body = _body_need_row(db, record['source_event_ids'][0])
            if body['agent_id'] != agent_id or body['native_tick'] != record['tick_after']:
                raise ValueError('Phase-4 affect-trace body source mismatch')
            count += 1
        operations = 0
        for operation_id, kind, agent_id, native_hash, ids, result in db.execute(
                'SELECT operation_id,kind,agent_id,native_state_hash,affect_trace_ids,result FROM phase4_operations ORDER BY seq'):
            if not operation_id or kind != 'capture' or agent_id not in meta['actors']:
                raise ValueError('Phase-4 operation mismatch')
            if not isinstance(native_hash, str) or len(native_hash) != 64 or not isinstance(json.loads(ids), list):
                raise ValueError('Phase-4 operation envelope is invalid')
            json.loads(result)
            operations += 1
        return dict(phase3_result, phase4_verified=True, affect_traces=count,
                    phase4_operations=operations, phase4_schema=meta['schema'])


def save(path, destination):
    destination = _ensure_new_destination(destination)
    weather.save(path, destination)
    return inspect(destination)
