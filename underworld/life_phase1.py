"""Phase-1 ALICE-LIFE-2 persistence for identity and private observations.

Phase 1 is deliberately copy-only.  It enrolls an existing native weather
world or ALICE-LIFE-1 copy into a new destination, then stores immutable Phase
0 identity and private-native observation records in sidecar tables.  Native
weather/life tables remain authoritative and are never rewritten by capture.
"""

from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from . import life_store, weather_store as weather
from .lease import Lease
from . import life_contracts as contracts


PROFILE = contracts.PROFILE
SCHEMA = 'ALICE-LIFE-2-PHASE-1'
VERSION = 1
MAX_OBSERVATIONS = 25000
TABLES = {'phase1_meta', 'phase1_identity', 'phase1_observations', 'phase1_operations'}


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
        raise ValueError('Phase-1 destination must be a NEW path; never overwrite a life')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def _actors(world, agents=None):
    available = sorted(entity['entity_id'] for entity in world.snapshot()['entities']
                       if entity.get('kind') == 'actor')
    if agents is None:
        return available
    selected = list(agents)
    if not selected or len(set(selected)) != len(selected):
        raise ValueError('Phase-1 agents must be unique and non-empty')
    if any(agent not in available for agent in selected):
        raise ValueError('Phase-1 agent is not a native actor in the source world')
    return selected


def _source_copy(source, destination, mode='connected'):
    source = Path(source).resolve()
    source_hash = _file_hash(source)
    if _has_tables(source, TABLES):
        raise ValueError('Source already contains Phase-1 records; use save for a backup')
    if _has_tables(source, {'life_meta', 'life_head', 'life_operations'}):
        weather.save(source, destination)
    else:
        life_store.attach(source, destination, mode=mode)
    if _file_hash(source) != source_hash:
        raise ValueError('Source world changed during Phase-1 attach')
    return source_hash


def _record_source_ids(native_hash, run_id, agent_id, tick):
    return [f'native-head:{native_hash}', f'native-observation:{run_id}:{agent_id}:{tick}']


def _identity(agent_id, run_id, tick, native_hash):
    # No name or trait is invented here.  The native actor identifier is the
    # explicit public label until a later authored identity operation exists.
    return contracts.identity(
        agent_id=agent_id,
        run_id=run_id,
        native_tick=tick,
        observation_version=tick,
        public_name=agent_id,
        authored_traits={},
        acquired_self_model={},
        source_event_ids=[f'native-head:{native_hash}'],
    )


def _observation(native, native_hash):
    return contracts.observation(
        agent_id=native['agent_id'],
        run_id=native['run_id'],
        native_tick=int(native['tick']),
        observation_version=int(native['tick']),
        own_state=native['own_state'],
        visible_entities=native['visible_entities'],
        audible_reports=native.get('audible_reports'),
        read_reports=native.get('read_reports'),
        social_reports=native.get('social_reports'),
        recent_action_results=native.get('recent_action_results'),
        omissions=native.get('omissions'),
        source_event_ids=_record_source_ids(native_hash, native['run_id'], native['agent_id'], native['tick']),
    )


def _meta(db):
    row = db.execute('SELECT payload,checksum FROM phase1_meta WHERE singleton=1').fetchone()
    if row is None:
        raise ValueError('Phase-1 metadata is missing')
    payload, checksum = row
    if _hash_text(payload) != checksum:
        raise ValueError('Phase-1 metadata checksum mismatch')
    value = json.loads(payload)
    if value.get('schema') != SCHEMA or value.get('profile') != PROFILE or value.get('version') != VERSION:
        raise ValueError('Unsupported Phase-1 schema')
    return value


def _write_meta(db, value):
    payload = _dumps(value)
    db.execute('UPDATE phase1_meta SET payload=?,checksum=? WHERE singleton=1', (payload, _hash_text(payload)))


def _create_tables(db):
    db.executescript('''
        CREATE TABLE phase1_meta(
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase1_identity(
            agent_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE TABLE phase1_observations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL UNIQUE,
            agent_id TEXT NOT NULL,
            native_tick INTEGER NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL
        );
        CREATE INDEX phase1_observation_agent_tick
            ON phase1_observations(agent_id, native_tick, seq);
        CREATE TABLE phase1_operations(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_id TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL,
            agent_id TEXT,
            native_state_hash TEXT NOT NULL,
            record_ids TEXT NOT NULL,
            result TEXT NOT NULL
        );
    ''')


def _insert_identity(db, record):
    payload = _dumps(record)
    db.execute('INSERT INTO phase1_identity VALUES(?,?,?)',
               (record['agent_id'], payload, record['checksum']))


def _insert_observation(db, record, observation_id):
    payload = _dumps(record)
    db.execute(
        'INSERT INTO phase1_observations(observation_id,agent_id,native_tick,payload,checksum) VALUES(?,?,?,?,?)',
        (observation_id, record['agent_id'], record['native_tick'], payload, record['checksum']))


def _insert_operation(db, operation_id, kind, agent_id, native_hash, record_ids, result):
    db.execute(
        'INSERT INTO phase1_operations(operation_id,kind,agent_id,native_state_hash,record_ids,result) VALUES(?,?,?,?,?,?)',
        (operation_id, kind, agent_id, native_hash, _dumps(record_ids), _dumps(result)))


def attach(source, destination, *, agents=None, mode='connected'):
    """Create a new Phase-1 copy and persist initial identities/observations."""
    destination = _ensure_new_destination(destination)
    source_hash = _source_copy(source, destination, mode=mode)
    try:
        with Lease(destination), closing(weather.connect(destination, False)) as db:
            db.execute('BEGIN IMMEDIATE')
            world, native_meta, _, life_meta = life_store.head(db)
            native_hash = weather.digest(world.checkpoint())
            run_id = world.snapshot()['run_id']
            selected = _actors(world, agents)
            observations = world.observe_batch(selected)
            _create_tables(db)
            meta = {
                'schema': SCHEMA,
                'profile': PROFILE,
                'version': VERSION,
                'run_id': run_id,
                'actors': selected,
                'source_db_sha256': source_hash,
                'source_native_state_hash': native_hash,
                'initial_native_state_hash': native_hash,
                'native_schema': native_meta.get('format', 'ALICE-WEATHER-2'),
                'life_schema': life_meta.get('format', 'ALICE-LIFE-1'),
                'operation_quota': MAX_OBSERVATIONS,
            }
            meta_text = _dumps(meta)
            db.execute('INSERT INTO phase1_meta VALUES(1,?,?)', (meta_text, _hash_text(meta_text)))
            for native in observations:
                identity_record = _identity(native['agent_id'], run_id, int(native['tick']), native_hash)
                observation_record = _observation(native, native_hash)
                _insert_identity(db, identity_record)
                observation_id = f'attach:{run_id}:{native["agent_id"]}:{native["tick"]}:{native_hash[:16]}'
                _insert_observation(db, observation_record, observation_id)
                _insert_operation(db, observation_id, 'attach', native['agent_id'], native_hash,
                                  [identity_record['agent_id'], observation_id],
                                  {'identity_checksum': identity_record['checksum'],
                                   'observation_checksum': observation_record['checksum']})
            db.commit()
    except BaseException:
        Path(destination).unlink(missing_ok=True)
        raise
    return inspect(destination)


def capture(path, *, agents=None):
    """Persist one private native observation per selected actor at current head."""
    path = Path(path).resolve()
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        meta = _meta(db)
        world, _, _, _ = life_store.head(db)
        native_hash = weather.digest(world.checkpoint())
        selected = _actors(world, agents)
        if db.execute('SELECT COUNT(*) FROM phase1_observations').fetchone()[0] + len(selected) > MAX_OBSERVATIONS:
            raise ValueError('Phase-1 observation quota reached; do not reset this life')
        inserted = []
        for native in world.observe_batch(selected):
            observation_record = _observation(native, native_hash)
            observation_id = f'capture:{native["run_id"]}:{native["agent_id"]}:{native["tick"]}:{native_hash[:16]}'
            prior = db.execute('SELECT checksum FROM phase1_observations WHERE observation_id=?', (observation_id,)).fetchone()
            if prior is not None:
                if prior[0] != observation_record['checksum']:
                    raise ValueError('Phase-1 observation identity collision')
                continue
            _insert_observation(db, observation_record, observation_id)
            _insert_operation(db, observation_id, 'capture', native['agent_id'], native_hash,
                              [observation_id], {'observation_checksum': observation_record['checksum']})
            inserted.append(observation_id)
        meta['last_native_state_hash'] = native_hash
        meta['last_native_tick'] = int(world.snapshot()['tick'])
        _write_meta(db, meta)
        db.commit()
    return inspect(path) | {'captured_observation_ids': inserted}


def identities(path):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        return [contracts.verify(json.loads(payload)) for payload, _ in db.execute(
            'SELECT payload,checksum FROM phase1_identity ORDER BY agent_id')]


def observations(path, *, agent_id=None):
    with closing(weather.connect(Path(path).resolve())) as db:
        _meta(db)
        if agent_id is None:
            rows = db.execute('SELECT payload FROM phase1_observations ORDER BY seq').fetchall()
        else:
            rows = db.execute('SELECT payload FROM phase1_observations WHERE agent_id=? ORDER BY seq', (agent_id,)).fetchall()
        return [contracts.verify(json.loads(row[0])) for row in rows]


def inspect(path):
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        world, _, _, _ = life_store.head(db)
        native = world.snapshot()
        return {
            'schema': meta['schema'],
            'profile': meta['profile'],
            'version': meta['version'],
            'run_id': meta['run_id'],
            'actors': list(meta['actors']),
            'native_tick': int(native['tick']),
            'native_simulated_time_s': float(native['simulated_time_s']),
            'native_state_hash': weather.digest(world.checkpoint()),
            'source_db_sha256': meta['source_db_sha256'],
            'source_native_state_hash': meta['source_native_state_hash'],
            'last_native_state_hash': meta.get('last_native_state_hash', meta['initial_native_state_hash']),
            'identity_count': db.execute('SELECT COUNT(*) FROM phase1_identity').fetchone()[0],
            'observation_count': db.execute('SELECT COUNT(*) FROM phase1_observations').fetchone()[0],
            'operation_count': db.execute('SELECT COUNT(*) FROM phase1_operations').fetchone()[0],
        }


def replay(path):
    """Verify Phase-0 checksums and the Phase-1 operation/record chain."""
    with closing(weather.connect(Path(path).resolve())) as db:
        meta = _meta(db)
        identities_by_agent = {}
        for agent_id, payload, stored_checksum in db.execute('SELECT agent_id,payload,checksum FROM phase1_identity ORDER BY agent_id'):
            record = contracts.verify(json.loads(payload))
            if record['agent_id'] != agent_id or record['checksum'] != stored_checksum:
                raise ValueError('Phase-1 identity row mismatch')
            identities_by_agent[agent_id] = record
        observation_ids = set()
        for observation_id, agent_id, payload, stored_checksum in db.execute(
                'SELECT observation_id,agent_id,payload,checksum FROM phase1_observations ORDER BY seq'):
            record = contracts.verify(json.loads(payload))
            if record['agent_id'] != agent_id or record['checksum'] != stored_checksum or observation_id in observation_ids:
                raise ValueError('Phase-1 observation row mismatch')
            if agent_id not in identities_by_agent:
                raise ValueError('Phase-1 observation has no identity')
            observation_ids.add(observation_id)
        operation_count = 0
        for operation_id, kind, agent_id, native_hash, record_ids, result in db.execute(
                'SELECT operation_id,kind,agent_id,native_state_hash,record_ids,result FROM phase1_operations ORDER BY seq'):
            ids = json.loads(record_ids)
            if not ids or operation_id not in ids or kind not in ('attach', 'capture'):
                raise ValueError('Phase-1 operation mismatch')
            if agent_id is not None and agent_id not in identities_by_agent:
                raise ValueError('Phase-1 operation has unknown agent')
            if not isinstance(native_hash, str) or len(native_hash) != 64:
                raise ValueError('Phase-1 operation native hash is invalid')
            json.loads(result)
            operation_count += 1
        return {
            'verified': True,
            'schema': meta['schema'],
            'profile': meta['profile'],
            'identities': len(identities_by_agent),
            'observations': len(observation_ids),
            'operations': operation_count,
        }


def save(path, destination):
    """Create an immutable backup of a Phase-1 destination."""
    destination = _ensure_new_destination(destination)
    weather.save(path, destination)
    return inspect(destination)
