"""Phase-3 ALICE-LIFE-2 native body-need persistence.

Phase 3 builds on a Phase-2 destination and stores immutable snapshots of the
native actor body state.  The native world remains authoritative for action
legality, resource transfer, health changes and death; this module records
those facts and does not create survival actions or alter mortality.
"""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from . import life_contracts as contracts
from . import life_phase1 as phase1
from . import life_phase2 as phase2
from . import weather_store as weather
from .lease import Lease


PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-3'
VERSION = 1
MAX_BODY_NEEDS = 25000
TABLES = {'phase3_meta', 'phase3_body_needs', 'phase3_operations'}


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
        raise ValueError('Phase-3 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase3_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-3 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-3 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-3 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase3_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase3_meta(
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase3_body_needs(
            body_need_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            native_tick INTEGER NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE INDEX phase3_body_agent_tick
            ON phase3_body_needs(agent_id, native_tick, body_need_id);
        CREATE TABLE phase3_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            native_state_hash TEXT NOT NULL,
            body_need_ids TEXT NOT NULL,
            result TEXT NOT NULL
        );
    ''')


def _observation_row(db, observation_id):
    row = db.execute('SELECT agent_id,payload FROM phase1_observations WHERE observation_id=?', (observation_id,)).fetchone()
    if row is None:
        raise ValueError('body need source observation is missing')
    agent_id, payload = row
    record = contracts.verify(json.loads(payload))
    if record['agent_id'] != agent_id or record['record_type'] != 'observation':
        raise ValueError('body need source observation row mismatch')
    return record


def _observation_id(db, agent_id, tick):
    row = db.execute(
        'SELECT observation_id FROM phase1_observations WHERE agent_id=? AND native_tick=? ORDER BY seq DESC LIMIT 1',
        (agent_id, tick)).fetchone()
    if row is None:
        raise ValueError('body need requires a persisted Phase-1 observation at the same native tick')
    return row[0]


def _body_record(native, observation_id, run_id):
    own_state = native['own_state']
    body = own_state.get('body')
    if not isinstance(body, dict):
        raise ValueError('native observation has no body state')
    required = ('hunger', 'thirst', 'fatigue', 'health', 'alive')
    if any(key not in body for key in required):
        raise ValueError('native observation body state is incomplete')
    return contracts.body_need(
        agent_id=native['agent_id'], run_id=run_id,
        native_tick=int(native['tick']), observation_version=int(native['tick']),
        hunger=body['hunger'], thirst=body['thirst'], fatigue=body['fatigue'],
        health=body['health'], alive=body['alive'], source_event_ids=[observation_id],
        provenance='native', privacy_scope='private', branch_id='main')


def _insert_operation(db, operation_id, kind, agent_id, native_hash, ids, result):
    db.execute(
        'INSERT INTO phase3_operations(operation_id,kind,agent_id,native_state_hash,body_need_ids,result) VALUES(?,?,?,?,?,?)',
        (operation_id, kind, agent_id, native_hash, _dumps(ids), _dumps(result)))


def attach(source, destination):
    """Create a new Phase-3 copy from a Phase-2 destination."""
    source = Path(source).resolve()
    destination = _ensure_new_destination(destination)
    if not _has_tables(source, phase2.TABLES):
        raise ValueError('Phase-3 attach requires a Phase-2 destination')
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-3 records; use save for a backup')
    source_hash = _file_hash(source)
    weather.save(source, destination)
    try:
        if _file_hash(source) != source_hash:
            raise ValueError('Source changed during Phase-3 attach')
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            phase2_meta = phase2._meta(db)
            world, _, _, _ = phase1.life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            meta = {
                'schema': SCHEMA,
                'profile': PROFILE,
                'version': VERSION,
                'run_id': phase2_meta['run_id'],
                'actors': list(phase2_meta['actors']),
                'source_db_sha256': source_hash,
                'phase2_source_hash': source_hash,
                'source_native_state_hash': native_hash,
                'operation_quota': MAX_BODY_NEEDS,
            }
            _create_tables(db)
            payload = _dumps(meta)
            db.execute('INSERT INTO phase3_meta VALUES(1,?,?)', (payload, _hash_text(payload)))
            db.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    # The initial Phase-1 observations are the authoritative body source.
    return capture(destination)


def capture(path, *, agents=None):
    """Capture native body state after extending Phase-1 observations safely."""
    path = Path(path).resolve()
    with closing(weather.connect(path)) as db:
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
    selected = list(meta['actors'] if agents is None else agents)
    if not selected or len(set(selected)) != len(selected) or any(agent not in set(meta['actors']) for agent in selected):
        raise ValueError('Phase-3 agents must be unique enrolled actors')
    # Phase-1 capture is sidecar-only and ensures each body snapshot has an
    # exact private native observation reference in the same destination.
    phase1.capture(path, agents=selected)
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
        native_hash = weather.digest(world.checkpoint())
        snapshot = world.snapshot()
        if db.execute('SELECT COUNT(*) FROM phase3_body_needs').fetchone()[0] + len(selected) > MAX_BODY_NEEDS:
            raise ValueError('Phase-3 body-need quota reached; do not reset this life')
        inserted = []
        for native in world.observe_batch(selected):
            tick = int(native['tick'])
            observation_id = _observation_id(db, native['agent_id'], tick)
            observation = _observation_row(db, observation_id)
            if observation['run_id'] != native['run_id'] or observation['native_tick'] != tick:
                raise ValueError('body need source observation timing mismatch')
            record = _body_record(native, observation_id, meta['run_id'])
            body_need_id = f'body:{record["agent_id"]}:{record["native_tick"]}:{native_hash[:16]}'
            prior = db.execute('SELECT checksum FROM phase3_body_needs WHERE body_need_id=?', (body_need_id,)).fetchone()
            if prior is not None:
                if prior[0] != record['checksum']:
                    raise ValueError('Phase-3 body-need identity collision')
                continue
            payload = _dumps(record)
            db.execute('INSERT INTO phase3_body_needs VALUES(?,?,?,?,?)',
                       (body_need_id, record['agent_id'], record['native_tick'], payload, record['checksum']))
            _insert_operation(db, body_need_id, 'capture', record['agent_id'], native_hash, [body_need_id],
                              {'body_need_checksum': record['checksum'], 'observation_id': observation_id})
            inserted.append(body_need_id)
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = int(snapshot['tick'])
        _write_meta(db, meta)
        db.commit()
    return inspect(path) | {'captured_body_need_ids': inserted}


def body_need(path, body_need_id):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        row = db.execute('SELECT payload,checksum FROM phase3_body_needs WHERE body_need_id=?', (body_need_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-3 body need')
        payload, checksum = row
        record = contracts.verify(json.loads(payload))
        if record['checksum'] != checksum:
            raise ValueError('Phase-3 body-need row mismatch')
        return record


def body_needs(path, *, agent_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        if agent_id is not None and agent_id not in set(meta['actors']):
            raise ValueError('body-need owner is not enrolled in Phase 3')
        query = 'SELECT payload,checksum FROM phase3_body_needs'
        params = ()
        if agent_id is not None:
            query += ' WHERE agent_id=?'
            params = (agent_id,)
        query += ' ORDER BY native_tick,body_need_id'
        result = []
        for payload, checksum in db.execute(query, params):
            record = contracts.verify(json.loads(payload))
            if record['checksum'] != checksum:
                raise ValueError('Phase-3 body-need row mismatch')
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
            'source_db_sha256': meta['source_db_sha256'],
            'phase2_source_hash': meta['phase2_source_hash'],
            'body_need_count': db.execute('SELECT COUNT(*) FROM phase3_body_needs').fetchone()[0],
            'operation_count': db.execute('SELECT COUNT(*) FROM phase3_operations').fetchone()[0],
        }


def replay(path):
    """Verify Phase 1/2 and body-need records against their observations."""
    phase2_result = phase2.replay(path)
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        count = 0
        for body_need_id, agent_id, payload, stored_checksum in db.execute(
                'SELECT body_need_id,agent_id,payload,checksum FROM phase3_body_needs ORDER BY native_tick,body_need_id'):
            record = contracts.verify(json.loads(payload))
            if record['record_type'] != 'body_need' or record['agent_id'] != agent_id or record['checksum'] != stored_checksum:
                raise ValueError('Phase-3 body-need row mismatch')
            if record['run_id'] != meta['run_id'] or record['privacy_scope'] != 'private' or record['provenance'] != 'native':
                raise ValueError('Phase-3 body-need ownership/privacy mismatch')
            if not body_need_id.startswith(f'body:{agent_id}:{record["native_tick"]}:'):
                raise ValueError('Phase-3 body-need identity mismatch')
            if not record['source_event_ids']:
                raise ValueError('Phase-3 body need has no observation source')
            observation = _observation_row(db, record['source_event_ids'][0])
            source_body = observation['own_state'].get('body', {})
            for key in ('hunger', 'thirst', 'fatigue', 'health', 'alive'):
                if record[key] != source_body.get(key):
                    raise ValueError('Phase-3 body need differs from native observation')
            count += 1
        operations = 0
        for operation_id, kind, agent_id, native_hash, ids, result in db.execute(
                'SELECT operation_id,kind,agent_id,native_state_hash,body_need_ids,result FROM phase3_operations ORDER BY seq'):
            if not operation_id or kind != 'capture' or agent_id not in meta['actors']:
                raise ValueError('Phase-3 operation mismatch')
            if not isinstance(native_hash, str) or len(native_hash) != 64 or not isinstance(json.loads(ids), list):
                raise ValueError('Phase-3 operation envelope is invalid')
            json.loads(result)
            operations += 1
        return dict(phase2_result, phase3_verified=True, body_needs=count,
                    phase3_operations=operations, phase3_schema=meta['schema'])


def save(path, destination):
    destination = _ensure_new_destination(destination)
    weather.save(path, destination)
    return inspect(destination)
