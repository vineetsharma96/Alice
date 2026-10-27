"""Phase-5 ALICE-LIFE-2 unified lineage coordinator.

Phase 5 does not add another inhabitant subsystem.  It binds the Phase 1
identity/observation, Phase 2 memory, Phase 3 body-need and Phase 4 affect
records into one replayable per-agent snapshot ledger.  Native life remains
authoritative and the coordinator is copy-only/read-only with respect to native
simulation state.
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
from . import life_phase4 as phase4
from . import weather_store as weather
from .lease import Lease


PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-5'
VERSION = 1
MAX_SNAPSHOTS = 25000
TABLES = {'phase5_meta', 'phase5_snapshots', 'phase5_operations'}


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
        raise ValueError('Phase-5 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase5_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-5 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-5 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-5 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase5_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase5_meta(
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase5_snapshots(
            snapshot_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            native_tick INTEGER NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE INDEX phase5_snapshot_agent_tick
            ON phase5_snapshots(agent_id, native_tick, snapshot_id);
        CREATE TABLE phase5_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            native_state_hash TEXT NOT NULL,
            snapshot_ids TEXT NOT NULL,
            result TEXT NOT NULL
        );
    ''')


def _identity(db, agent_id):
    row = db.execute('SELECT payload,checksum FROM phase1_identity WHERE agent_id=?', (agent_id,)).fetchone()
    if row is None:
        raise ValueError('unified snapshot identity is missing')
    payload, checksum = row
    record = contracts.verify(json.loads(payload))
    if record['checksum'] != checksum or record['agent_id'] != agent_id:
        raise ValueError('unified snapshot identity row mismatch')
    return record


def _observation(db, agent_id, tick):
    row = db.execute(
        'SELECT observation_id,payload,checksum FROM phase1_observations WHERE agent_id=? AND native_tick=? ORDER BY seq DESC LIMIT 1',
        (agent_id, tick)).fetchone()
    if row is None:
        raise ValueError('unified snapshot observation is missing')
    observation_id, payload, checksum = row
    record = contracts.verify(json.loads(payload))
    if record['checksum'] != checksum or record['agent_id'] != agent_id:
        raise ValueError('unified snapshot observation row mismatch')
    return observation_id, record


def _body(db, agent_id, tick):
    row = db.execute(
        'SELECT body_need_id,payload,checksum FROM phase3_body_needs WHERE agent_id=? AND native_tick=? ORDER BY rowid DESC LIMIT 1',
        (agent_id, tick)).fetchone()
    if row is None:
        raise ValueError('unified snapshot body need is missing')
    body_id, payload, checksum = row
    record = contracts.verify(json.loads(payload))
    if record['checksum'] != checksum or record['agent_id'] != agent_id:
        raise ValueError('unified snapshot body row mismatch')
    return body_id, record


def _affect(db, agent_id, tick):
    row = db.execute(
        'SELECT affect_trace_id,payload,checksum FROM phase4_affect_traces WHERE agent_id=? AND tick_after=? ORDER BY rowid DESC LIMIT 1',
        (agent_id, tick)).fetchone()
    if row is None:
        raise ValueError('unified snapshot affect trace is missing')
    trace_id, payload, checksum = row
    record = contracts.verify(json.loads(payload))
    if record['checksum'] != checksum or record['agent_id'] != agent_id:
        raise ValueError('unified snapshot affect row mismatch')
    return trace_id, record


def _memories(db, agent_id, observation_id, observation):
    refs = {observation_id, *observation['source_event_ids']}
    found = []
    for memory_id, payload, checksum in db.execute('SELECT memory_id,payload,checksum FROM phase2_memories WHERE agent_id=?', (agent_id,)):
        record = contracts.verify(json.loads(payload))
        if record['checksum'] != checksum:
            raise ValueError('unified snapshot memory row mismatch')
        if refs.intersection(record['source_event_ids']):
            found.append({'memory_id': memory_id, 'checksum': record['checksum'],
                          'validity': record['validity']})
    return sorted(found, key=lambda item: item['memory_id'])


def _snapshot_record(meta, agent_id, tick, identity, observation_id, observation,
                     body_id, body, affect_id, affect, memories):
    value = {
        'profile': PROFILE, 'schema': SCHEMA, 'version': VERSION,
        'run_id': meta['run_id'], 'branch_id': 'main', 'agent_id': agent_id,
        'native_tick': tick, 'observation_version': tick,
        'identity': {'agent_id': agent_id, 'checksum': identity['checksum']},
        'observation': {'observation_id': observation_id, 'checksum': observation['checksum']},
        'memory': memories,
        'body_need': {'body_need_id': body_id, 'checksum': body['checksum']},
        'affect_trace': {'affect_trace_id': affect_id, 'checksum': affect['checksum']},
    }
    value['lineage_checksum'] = _hash_text(_dumps(value))
    return value


def _verify_snapshot(snapshot):
    required = {'profile', 'schema', 'version', 'run_id', 'branch_id', 'agent_id',
                'native_tick', 'observation_version', 'identity', 'observation',
                'memory', 'body_need', 'affect_trace', 'lineage_checksum'}
    if set(snapshot) != required:
        raise ValueError('unified snapshot fields mismatch')
    if snapshot['profile'] != PROFILE or snapshot['schema'] != SCHEMA or snapshot['version'] != VERSION:
        raise ValueError('unified snapshot schema mismatch')
    if type(snapshot['native_tick']) is not int or snapshot['native_tick'] < 0:
        raise ValueError('unified snapshot tick is invalid')
    expected = dict(snapshot)
    expected.pop('lineage_checksum')
    if snapshot['lineage_checksum'] != _hash_text(_dumps(expected)):
        raise ValueError('unified snapshot lineage checksum mismatch')
    for key in ('identity', 'observation', 'body_need', 'affect_trace'):
        if not isinstance(snapshot[key], dict) or not isinstance(snapshot[key].get('checksum'), str):
            raise ValueError('unified snapshot source binding is invalid')
    if not isinstance(snapshot['memory'], list) or any(not isinstance(item, dict) for item in snapshot['memory']):
        raise ValueError('unified snapshot memory binding is invalid')
    return snapshot


def _insert_operation(db, operation_id, kind, agent_id, native_hash, ids, result):
    db.execute(
        'INSERT INTO phase5_operations(operation_id,kind,agent_id,native_state_hash,snapshot_ids,result) VALUES(?,?,?,?,?,?)',
        (operation_id, kind, agent_id, native_hash, _dumps(ids), _dumps(result)))


def attach(source, destination):
    """Create a new Phase-5 unified copy from a Phase-4 destination."""
    source = Path(source).resolve()
    destination = _ensure_new_destination(destination)
    if not _has_tables(source, phase4.TABLES):
        raise ValueError('Phase-5 attach requires a Phase-4 destination')
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-5 records; use save for a backup')
    source_hash = _file_hash(source)
    weather.save(source, destination)
    try:
        if _file_hash(source) != source_hash:
            raise ValueError('Source changed during Phase-5 attach')
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            phase4_meta = phase4._meta(db)
            world, _, _, _ = phase1.life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            meta = {
                'schema': SCHEMA, 'profile': PROFILE, 'version': VERSION,
                'run_id': phase4_meta['run_id'], 'actors': list(phase4_meta['actors']),
                'source_db_sha256': source_hash, 'phase4_source_hash': source_hash,
                'source_native_state_hash': native_hash, 'operation_quota': MAX_SNAPSHOTS,
            }
            _create_tables(db)
            payload = _dumps(meta)
            db.execute('INSERT INTO phase5_meta VALUES(1,?,?)', (payload, _hash_text(payload)))
            db.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return capture(destination)


def capture(path, *, agents=None):
    """Capture one cross-subsystem lineage snapshot per enrolled agent."""
    path = Path(path).resolve()
    with closing(weather.connect(path)) as db:
        meta = _meta(db)
    selected = list(meta['actors'] if agents is None else agents)
    if not selected or len(set(selected)) != len(selected) or any(agent not in set(meta['actors']) for agent in selected):
        raise ValueError('Phase-5 agents must be unique enrolled actors')
    phase4.capture(path, agents=selected)
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        world, _, _, _ = phase1.life_store.head(db)
        tick = int(world.snapshot()['tick'])
        native_hash = weather.digest(world.checkpoint())
        if db.execute('SELECT COUNT(*) FROM phase5_snapshots').fetchone()[0] + len(selected) > MAX_SNAPSHOTS:
            raise ValueError('Phase-5 snapshot quota reached; do not reset this life')
        inserted = []
        for agent_id in selected:
            identity = _identity(db, agent_id)
            observation_id, observation = _observation(db, agent_id, tick)
            body_id, body = _body(db, agent_id, tick)
            affect_id, affect = _affect(db, agent_id, tick)
            memories = _memories(db, agent_id, observation_id, observation)
            snapshot = _snapshot_record(meta, agent_id, tick, identity, observation_id, observation,
                                        body_id, body, affect_id, affect, memories)
            snapshot_id = f'bundle:{agent_id}:{tick}:{native_hash[:16]}'
            prior = db.execute('SELECT payload,checksum FROM phase5_snapshots WHERE snapshot_id=?', (snapshot_id,)).fetchone()
            if prior is not None:
                payload, checksum = prior
                existing = _verify_snapshot(json.loads(payload))
                if existing['lineage_checksum'] != checksum:
                    raise ValueError('Phase-5 snapshot row mismatch')
                continue
            payload = _dumps(snapshot)
            db.execute('INSERT INTO phase5_snapshots VALUES(?,?,?,?,?)',
                       (snapshot_id, agent_id, tick, payload, snapshot['lineage_checksum']))
            _insert_operation(db, snapshot_id, 'capture', agent_id, native_hash, [snapshot_id],
                              {'lineage_checksum': snapshot['lineage_checksum']})
            inserted.append(snapshot_id)
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = tick
        _write_meta(db, meta)
        db.commit()
    return inspect(path) | {'captured_snapshot_ids': inserted}


def snapshot(path, snapshot_id):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        row = db.execute('SELECT payload,checksum FROM phase5_snapshots WHERE snapshot_id=?', (snapshot_id,)).fetchone()
        if row is None:
            raise ValueError('unknown Phase-5 snapshot')
        payload, checksum = row
        value = _verify_snapshot(json.loads(payload))
        if value['lineage_checksum'] != checksum:
            raise ValueError('Phase-5 snapshot row mismatch')
        return value


def snapshots(path, *, agent_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        if agent_id is not None and agent_id not in set(meta['actors']):
            raise ValueError('snapshot owner is not enrolled in Phase 5')
        query = 'SELECT snapshot_id,payload,checksum FROM phase5_snapshots'
        params = ()
        if agent_id is not None:
            query += ' WHERE agent_id=?'
            params = (agent_id,)
        query += ' ORDER BY native_tick,snapshot_id'
        result = []
        for snapshot_id, payload, checksum in db.execute(query, params):
            value = _verify_snapshot(json.loads(payload))
            if value['lineage_checksum'] != checksum:
                raise ValueError('Phase-5 snapshot row mismatch')
            result.append({'snapshot_id': snapshot_id, 'record': value})
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
            'source_db_sha256': meta['source_db_sha256'], 'phase4_source_hash': meta['phase4_source_hash'],
            'snapshot_count': db.execute('SELECT COUNT(*) FROM phase5_snapshots').fetchone()[0],
            'operation_count': db.execute('SELECT COUNT(*) FROM phase5_operations').fetchone()[0],
        }


def replay(path):
    """Verify Phase 1-4 and the cross-subsystem snapshot ledger."""
    phase4_result = phase4.replay(path)
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        count = 0
        for snapshot_id, agent_id, payload, stored_checksum in db.execute(
                'SELECT snapshot_id,agent_id,payload,checksum FROM phase5_snapshots ORDER BY native_tick,snapshot_id'):
            value = _verify_snapshot(json.loads(payload))
            if value['agent_id'] != agent_id or value['run_id'] != meta['run_id'] or value['lineage_checksum'] != stored_checksum:
                raise ValueError('Phase-5 snapshot owner/row mismatch')
            if not snapshot_id.startswith(f'bundle:{agent_id}:{value["native_tick"]}:'):
                raise ValueError('Phase-5 snapshot identity mismatch')
            identity = _identity(db, agent_id)
            observation_id, observation = _observation(db, agent_id, value['native_tick'])
            body_id, body = _body(db, agent_id, value['native_tick'])
            affect_id, affect = _affect(db, agent_id, value['native_tick'])
            if value['identity']['checksum'] != identity['checksum'] or value['observation']['observation_id'] != observation_id:
                raise ValueError('Phase-5 identity/observation lineage mismatch')
            if value['observation']['checksum'] != observation['checksum'] or value['body_need']['body_need_id'] != body_id:
                raise ValueError('Phase-5 observation/body lineage mismatch')
            if value['body_need']['checksum'] != body['checksum'] or value['affect_trace']['affect_trace_id'] != affect_id:
                raise ValueError('Phase-5 body/affect lineage mismatch')
            if value['affect_trace']['checksum'] != affect['checksum']:
                raise ValueError('Phase-5 affect lineage mismatch')
            expected_memories = _memories(db, agent_id, observation_id, observation)
            if value['memory'] != expected_memories:
                raise ValueError('Phase-5 memory lineage mismatch')
            count += 1
        operations = 0
        for operation_id, kind, agent_id, native_hash, ids, result in db.execute(
                'SELECT operation_id,kind,agent_id,native_state_hash,snapshot_ids,result FROM phase5_operations ORDER BY seq'):
            if not operation_id or kind != 'capture' or agent_id not in meta['actors']:
                raise ValueError('Phase-5 operation mismatch')
            if not isinstance(native_hash, str) or len(native_hash) != 64 or not isinstance(json.loads(ids), list):
                raise ValueError('Phase-5 operation envelope is invalid')
            json.loads(result)
            operations += 1
        return dict(phase4_result, phase5_verified=True, snapshots=count,
                    phase5_operations=operations, phase5_schema=meta['schema'])


def save(path, destination):
    destination = _ensure_new_destination(destination)
    weather.save(path, destination)
    return inspect(destination)
