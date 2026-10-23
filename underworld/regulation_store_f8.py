"""Durable, copy-only F8 emotional-regulation overlay.

The native world remains authoritative for observations and action receipts. F8
stores only one owner's bounded regulation efficacy learned from own snapshots
and native-shaped results; it never changes the native scheduler or action
state.
"""

from contextlib import closing
import hashlib
import json
import sqlite3
from pathlib import Path

from . import regulation_f8 as regulation
from . import storage


def dumps(value):
    """Canonical JSON without the shallow wire-format nesting limit."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def loads(text):
    return json.loads(text)


SCHEMA = "alice-regulation-store-f8-1"
MAX_OPERATIONS = 25000
EMPTY_HASH = hashlib.sha256(b"{}").hexdigest()
TABLES = ("f8_meta", "f8_regulation", "f8_operations")


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_database(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("source world does not exist")
    if destination.exists():
        raise FileExistsError("F8 attach requires a NEW destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    with destination.open("xb"):
        pass
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(destination)) as target:
            origin.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("F8 destination backup integrity check failed")
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed during F8 attach")
    return source_hash


def _actors(world):
    return sorted(entity["entity_id"] for entity in world.snapshot()["entities"]
                   if entity.get("kind") == "actor")


def _state_hash(states):
    rows = [{"owner": owner, "state": states[owner]}
            for owner in sorted(states)]
    return hashlib.sha256(dumps(rows).encode("utf-8")).hexdigest()


def _initial_states(actors, run_id):
    return {owner: regulation.initial(owner, run_id) for owner in actors}


def _meta_read(db):
    row = db.execute("SELECT payload,checksum FROM f8_meta WHERE singleton=1").fetchone()
    if row is None or hashlib.sha256(row[0].encode("utf-8")).hexdigest() != row[1]:
        raise ValueError("F8 metadata checksum mismatch")
    meta = loads(row[0])
    if meta.get("schema") != SCHEMA:
        raise ValueError("unsupported F8 regulation schema")
    run_id = db.execute("SELECT run_id FROM run WHERE singleton=1").fetchone()[0]
    if meta.get("run_id") != run_id:
        raise ValueError("F8 run identity mismatch")
    return meta


def _meta_write(db, meta):
    text = dumps(meta)
    db.execute("UPDATE f8_meta SET payload=?,checksum=? WHERE singleton=1",
               (text, hashlib.sha256(text.encode("utf-8")).hexdigest()))


def _read_states(db, meta):
    states = {}
    for owner, payload, checksum in db.execute(
            "SELECT owner,payload,checksum FROM f8_regulation ORDER BY owner"):
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != checksum:
            raise ValueError("F8 regulation checksum mismatch")
        state = loads(payload)
        if state.get("owner") != owner:
            raise ValueError("F8 regulation identity mismatch")
        regulation.validate(state)
        states[owner] = state
    if set(states) != set(meta["actors"]):
        raise ValueError("F8 regulation set is incomplete")
    if _state_hash(states) != meta["state_hash"]:
        raise ValueError("F8 regulation head hash mismatch")
    return states


def _write_states(db, states):
    for owner, state in states.items():
        text = dumps(state)
        db.execute("UPDATE f8_regulation SET payload=?,checksum=? WHERE owner=?",
                   (text, hashlib.sha256(text.encode("utf-8")).hexdigest(), owner))


def _operation_id(command, operation_id):
    if operation_id is None:
        return "f8-op-" + hashlib.sha256(dumps(command).encode("utf-8")).hexdigest()[:32]
    if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
        raise ValueError("invalid F8 operation ID")
    return operation_id


def _native_current(world, owner, after):
    if type(owner) is not str or not owner:
        raise ValueError("invalid F8 owner")
    current = world.observe_batch([owner])[0]
    if after is not None and dumps(after) != dumps(current):
        raise ValueError("F8 after observation must match the current native observation")
    if current.get("agent_id") != owner:
        raise ValueError("F8 native observation identity mismatch")
    return current


def attach(source, destination):
    """Copy an existing general world and initialize one state per actor."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    source_hash = _copy_database(source, destination)
    source_after = _file_hash(source)
    try:
        with closing(storage._connect(destination)) as db:
            db.execute("BEGIN IMMEDIATE")
            world, _, metadata, _ = storage._head(db)
            if any(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                              (table,)).fetchone() for table in TABLES):
                raise ValueError("destination already contains F8 regulation tables")
            actors = _actors(world)
            states = _initial_states(actors, metadata["branch_id"])
            state_hash = _state_hash(states)
            meta = {"schema": SCHEMA, "run_id": metadata["branch_id"], "actors": actors,
                    "source_db_sha256": source_hash, "state_hash": state_hash,
                    "last_operation_id": None,
                    "initial_regulation": [{"owner": owner, "state": states[owner]}
                                            for owner in actors]}
            db.executescript("""
                CREATE TABLE f8_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f8_regulation(owner TEXT PRIMARY KEY,
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f8_operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE, command TEXT NOT NULL,
                    before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, result TEXT NOT NULL);
                CREATE INDEX f8_operations_identity ON f8_operations(operation_id);
            """)
            meta_text = dumps(meta)
            db.execute("INSERT INTO f8_meta VALUES(1,?,?)",
                       (meta_text, hashlib.sha256(meta_text.encode("utf-8")).hexdigest()))
            for owner, state in states.items():
                text = dumps(state)
                db.execute("INSERT INTO f8_regulation VALUES(?,?,?)",
                           (owner, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
            command = {"kind": "attach", "source_db_sha256": source_hash, "actors": actors}
            db.execute("INSERT INTO f8_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                       ("f8-attach-" + source_hash[:32], dumps(command), EMPTY_HASH, state_hash,
                        dumps({"event_count": 0, "changed": False})))
            db.commit()
    finally:
        if _file_hash(source) != source_after:
            raise ValueError("source world changed during F8 initialization")
    return inspect(destination)


def inspect(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        return {"schema": SCHEMA, "run_id": meta["run_id"], "actors": list(meta["actors"]),
                "state_hash": meta["state_hash"], "source_db_sha256": meta["source_db_sha256"],
                "operation_count": db.execute("SELECT COUNT(*) FROM f8_operations").fetchone()[0],
                "regulation": states}


def choose(path, owner, candidates):
    """Rank caller-provided feasible proposals using the current own snapshot."""
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        world, _, _, _ = storage._head(db)
        meta = _meta_read(db)
        if owner not in meta["actors"]:
            raise ValueError("unknown F8 owner")
        states = _read_states(db, meta)
        observation = world.observe_batch([owner])[0]
        return regulation.choose(observation, states[owner], candidates)


def record_outcome(path, owner, before, outcome, after=None, operation_id=None, fault=None):
    """Learn one outcome while requiring the after snapshot to be current."""
    with closing(storage._connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        world, _, _, _ = storage._head(db)
        meta = _meta_read(db)
        if owner not in meta["actors"]:
            raise ValueError("unknown F8 owner")
        current = _native_current(world, owner, after)
        command = {"kind": "record_outcome", "owner": owner, "before": before,
                   "after": current, "outcome": outcome}
        operation_id = _operation_id(command, operation_id)
        old = db.execute("SELECT command,result,before_hash,after_hash FROM f8_operations WHERE operation_id=?",
                         (operation_id,)).fetchone()
        if old:
            if old[0] != dumps(command):
                raise ValueError("conflicting F8 operation identity")
            result = loads(old[1])
            db.commit()
            return dict(result, operation_id=operation_id, before_hash=old[2],
                        after_hash=old[3], idempotent=True)
        states = _read_states(db, meta)
        before_hash = _state_hash(states)
        evidence = regulation.observe_outcome(states[owner], before, current, outcome)
        result = {"owner": owner, "evidence": evidence, "state": states[owner]}
        after_hash = _state_hash(states)
        if db.execute("SELECT COUNT(*) FROM f8_operations").fetchone()[0] >= MAX_OPERATIONS:
            raise ValueError("F8 operation journal limit reached")
        db.execute("INSERT INTO f8_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                   (operation_id, dumps(command), before_hash, after_hash, dumps(result)))
        _write_states(db, states)
        meta["state_hash"] = after_hash
        meta["last_operation_id"] = operation_id
        _meta_write(db, meta)
        if fault:
            fault("before_commit")
        db.commit()
    if fault:
        fault("after_commit")
    return dict(result, operation_id=operation_id, before_hash=before_hash,
                after_hash=after_hash, idempotent=False)


def record_current_outcome(path, owner, before, outcome, operation_id=None, fault=None):
    """Learn from the current native snapshot without accepting a forged after."""
    return record_outcome(path, owner, before, outcome, after=None,
                          operation_id=operation_id, fault=fault)


def save(path, destination):
    """Make a no-overwrite SQLite backup without changing the source world."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("F8 backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(storage._connect(path, readonly=True)) as source:
        with destination.open("xb"):
            pass
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("F8 backup integrity check failed")
    return inspect(destination)


def resume(path):
    result = inspect(path)
    result["replay"] = replay(path)
    return result


def replay(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = {entry["owner"]: entry["state"] for entry in meta["initial_regulation"]}
        operations = 0
        for _, command_text, before, after, result_text in db.execute(
                "SELECT operation_id,command,before_hash,after_hash,result FROM f8_operations ORDER BY seq"):
            command = loads(command_text)
            if command["kind"] == "attach":
                if before != EMPTY_HASH or after != _state_hash(states):
                    raise ValueError("F8 attach replay mismatch")
                expected_result = {"event_count": 0, "changed": False}
            elif command["kind"] == "record_outcome":
                if before != _state_hash(states):
                    raise ValueError("F8 operation chain mismatch")
                owner = command["owner"]
                if owner not in states:
                    raise ValueError("F8 replay references unknown owner")
                evidence = regulation.observe_outcome(states[owner], command["before"],
                                                       command["after"], command["outcome"])
                expected_result = {"owner": owner, "evidence": evidence,
                                   "state": states[owner]}
                if after != _state_hash(states):
                    raise ValueError("F8 operation after hash mismatch")
            else:
                raise ValueError("unknown F8 operation")
            if dumps(expected_result) != result_text:
                raise ValueError("F8 operation result mismatch")
            operations += 1
        stored = _read_states(db, meta)
        actual = _state_hash(states)
        if actual != _state_hash(stored) or actual != meta["state_hash"]:
            raise ValueError("F8 final replay mismatch")
        return {"replay_matches": True, "operations": operations, "state_hash": actual}


__all__ = ["SCHEMA", "attach", "inspect", "choose", "record_outcome",
           "record_current_outcome", "save", "resume", "replay"]
