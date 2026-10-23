"""Durable, copy-only F7 inference overlay for existing general worlds.

F7 stores only directional hypotheses derived from an observer's current native
observation and a strict public envelope.  Native state, target-private state,
operator labels, and scheduler behavior remain outside this journal.
"""

from contextlib import closing
import hashlib
import math
import sqlite3
from pathlib import Path

from . import others_f7 as inference
from . import storage
from .wire import dumps, loads


SCHEMA = "alice-others-store-f7-1"
MAX_OPERATIONS = 25000
EMPTY_HASH = hashlib.sha256(b"{}").hexdigest()
TABLES = ("f7_meta", "f7_inferences", "f7_operations")


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
        raise FileExistsError("F7 attach requires a NEW destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    with destination.open("xb"):
        pass
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
        with closing(sqlite3.connect(destination)) as target:
            origin.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("F7 destination backup integrity check failed")
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed during F7 attach")
    return source_hash


def _state_hash(states):
    rows = [{"observer": observer, "target": target,
             "state": states[(observer, target)]}
            for observer, target in sorted(states)]
    return hashlib.sha256(dumps(rows).encode("utf-8")).hexdigest()


def _actors(world):
    return sorted(entity["entity_id"] for entity in world.snapshot()["entities"]
                   if entity.get("kind") == "actor")


def _initial_states(actors):
    return {(observer, target): inference.initial(observer, target)
            for observer in actors for target in actors if observer != target}


def _meta_read(db):
    row = db.execute("SELECT payload,checksum FROM f7_meta WHERE singleton=1").fetchone()
    if row is None or hashlib.sha256(row[0].encode("utf-8")).hexdigest() != row[1]:
        raise ValueError("F7 metadata checksum mismatch")
    meta = loads(row[0])
    if meta.get("schema") != SCHEMA:
        raise ValueError("unsupported F7 inference schema")
    run_id = db.execute("SELECT run_id FROM run WHERE singleton=1").fetchone()[0]
    if meta.get("run_id") != run_id:
        raise ValueError("F7 run identity mismatch")
    return meta


def _meta_write(db, meta):
    text = dumps(meta)
    db.execute("UPDATE f7_meta SET payload=?,checksum=? WHERE singleton=1",
               (text, hashlib.sha256(text.encode("utf-8")).hexdigest()))


def _read_states(db, meta):
    states = {}
    for observer, target, payload, checksum in db.execute(
            "SELECT observer,target,payload,checksum FROM f7_inferences ORDER BY observer,target"):
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != checksum:
            raise ValueError("F7 inference checksum mismatch")
        state = loads(payload)
        if state.get("observer") != observer or state.get("target") != target:
            raise ValueError("F7 inference identity mismatch")
        inference.validate(state)
        states[(observer, target)] = state
    expected = {(observer, target) for observer in meta["actors"]
                for target in meta["actors"] if observer != target}
    if set(states) != expected:
        raise ValueError("F7 directional inference set is incomplete")
    if _state_hash(states) != meta["state_hash"]:
        raise ValueError("F7 inference head hash mismatch")
    return states


def _write_states(db, states):
    for (observer, target), state in states.items():
        text = dumps(state)
        db.execute("UPDATE f7_inferences SET payload=?,checksum=? WHERE observer=? AND target=?",
                   (text, hashlib.sha256(text.encode("utf-8")).hexdigest(), observer, target))


def _operation_id(command, operation_id):
    if operation_id is None:
        return "f7-op-" + hashlib.sha256(dumps(command).encode("utf-8")).hexdigest()[:32]
    if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
        raise ValueError("invalid F7 operation ID")
    return operation_id


def _public_envelope(envelope, observer, actors):
    if type(envelope) is not dict:
        raise ValueError("F7 requires a public observation envelope")
    if set(envelope) != {"observer", "target", "visible_cues", "social_reports"}:
        raise ValueError("F7 observation envelope must contain only public fields")
    if envelope["observer"] != observer or envelope["target"] not in actors:
        raise ValueError("Foreign F7 observation")
    # Run the estimator's strict public-field validation without changing a
    # durable state.  This rejects private target state and operator labels.
    probe = inference.initial(observer, envelope["target"])
    inference._validate_observation(probe, envelope)
    return {"observer": observer, "target": envelope["target"],
            "visible_cues": list(envelope["visible_cues"]),
            "social_reports": list(envelope["social_reports"])}


def _native_is_current(world, observer, observation):
    if type(observer) is not str or not observer:
        raise ValueError("invalid F7 observer")
    current = world.observe_batch([observer])[0]
    if observation is None:
        return current
    if type(observation) is not dict or observation.get("agent_id") != observer:
        raise ValueError("Foreign F7 native observation")
    if dumps(observation) != dumps(current):
        raise ValueError("F7 observation must match the current native observation")
    return current


def public_envelope_from_native(observation, target):
    """Derive conservative F7 cues from one permitted observer snapshot."""
    if type(observation) is not dict or type(observation.get("agent_id")) is not str:
        raise ValueError("F7 requires a native observation")
    visible = observation.get("visible_entities")
    if type(visible) is not list:
        raise ValueError("F7 native observation visibility is invalid")
    actor = next((item for item in visible
                  if isinstance(item, dict) and item.get("entity_id") == target
                  and item.get("kind") == "actor"), None)
    if actor is None:
        raise ValueError("F7 target is not publicly visible")
    position = actor.get("position_m")
    if type(position) not in (list, tuple) or len(position) != 2:
        raise ValueError("F7 target position is not publicly available")
    cues = []
    for entity in visible:
        if not isinstance(entity, dict) or entity.get("entity_id") == target:
            continue
        other_position = entity.get("position_m")
        if type(other_position) not in (list, tuple) or len(other_position) != 2:
            continue
        if math.dist(position, other_position) > 1.5:
            continue
        kind = entity.get("kind")
        if kind in ("food", "water"):
            cues.append({"source_event_id": f"visible:{target}:{entity['entity_id']}",
                         "cue": "watching_resource", "strength": 1.0})
        elif kind == "lean_to":
            cues.append({"source_event_id": f"visible:{target}:{entity['entity_id']}",
                         "cue": "seeking_shelter", "strength": 1.0})
    reports = []
    for report in observation.get("social_reports", []):
        if not isinstance(report, dict) or report.get("other") != target:
            continue
        kind = {"task_accepted": "accepted_help", "task_declined": "declined_help",
                "resource_given": "shared_resource"}.get(report.get("kind"))
        if kind:
            reports.append({"source_event_id": f"social:{report['source_event_seq']}",
                            "kind": kind, "strength": 1.0})
    return {"observer": observation["agent_id"], "target": target,
            "visible_cues": sorted(cues, key=lambda item: item["source_event_id"]),
            "social_reports": sorted(reports, key=lambda item: item["source_event_id"])}


def attach(source, destination):
    """Copy an existing general world, then initialize additive F7 tables."""
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
                raise ValueError("destination already contains F7 inference tables")
            actors = _actors(world)
            states = _initial_states(actors)
            state_hash = _state_hash(states)
            meta = {"schema": SCHEMA, "run_id": metadata["branch_id"], "actors": actors,
                    "source_db_sha256": source_hash, "state_hash": state_hash,
                    "last_operation_id": None,
                    "initial_inferences": [{"observer": observer, "target": target,
                                             "state": states[(observer, target)]}
                                            for observer, target in sorted(states)]}
            db.executescript("""
                CREATE TABLE f7_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f7_inferences(observer TEXT NOT NULL, target TEXT NOT NULL,
                    payload TEXT NOT NULL, checksum TEXT NOT NULL,
                    PRIMARY KEY(observer,target));
                CREATE TABLE f7_operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE, command TEXT NOT NULL,
                    before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, result TEXT NOT NULL);
                CREATE INDEX f7_operations_identity ON f7_operations(operation_id);
            """)
            meta_text = dumps(meta)
            db.execute("INSERT INTO f7_meta VALUES(1,?,?)",
                       (meta_text, hashlib.sha256(meta_text.encode("utf-8")).hexdigest()))
            for (observer, target), state in states.items():
                text = dumps(state)
                db.execute("INSERT INTO f7_inferences VALUES(?,?,?,?)",
                           (observer, target, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
            command = {"kind": "attach", "source_db_sha256": source_hash, "actors": actors}
            db.execute("INSERT INTO f7_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                       ("f7-attach-" + source_hash[:32], dumps(command), EMPTY_HASH, state_hash,
                        dumps({"event_count": 0, "changed": False})))
            db.commit()
    finally:
        if _file_hash(source) != source_after:
            raise ValueError("source world changed during F7 initialization")
    return inspect(destination)


def inspect(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        return {"schema": SCHEMA, "run_id": meta["run_id"], "actors": list(meta["actors"]),
                "state_hash": meta["state_hash"], "source_db_sha256": meta["source_db_sha256"],
                "operation_count": db.execute("SELECT COUNT(*) FROM f7_operations").fetchone()[0],
                "inferences": {f"{observer}->{target}": state
                               for (observer, target), state in states.items()}}


def record_observation(path, observer, observation=None, public_envelope=None,
                       envelope=None, operation_id=None, fault=None):
    """Record current observer-native validation plus one public target envelope."""
    if public_envelope is not None and envelope is not None:
        raise ValueError("provide only one F7 public envelope")
    if envelope is not None:
        public_envelope = envelope
    with closing(storage._connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        world, _, metadata, _ = storage._head(db)
        meta = _meta_read(db)
        normalized = _public_envelope(public_envelope, observer, meta["actors"])
        command = {"kind": "record_observation", "envelope": normalized}
        operation_id = _operation_id(command, operation_id)
        old = db.execute("SELECT command,result,before_hash,after_hash FROM f7_operations WHERE operation_id=?",
                         (operation_id,)).fetchone()
        if old:
            if old[0] != dumps(command):
                raise ValueError("conflicting F7 operation identity")
            result = loads(old[1])
            db.commit()
            return dict(result, operation_id=operation_id, before_hash=old[2],
                        after_hash=old[3], idempotent=True)

        native_observation = _native_is_current(world, observer, observation)
        if native_observation.get("agent_id") != observer:
            raise ValueError("F7 native observation identity mismatch")
        states = _read_states(db, meta)
        key = (observer, normalized["target"])
        if key not in states:
            raise ValueError("Foreign F7 observation target")
        before = _state_hash(states)
        result = inference.infer(states[key], normalized)
        after = _state_hash(states)
        if db.execute("SELECT COUNT(*) FROM f7_operations").fetchone()[0] >= MAX_OPERATIONS:
            raise ValueError("F7 operation journal limit reached")
        db.execute("INSERT INTO f7_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                   (operation_id, dumps(command), before, after, dumps(result)))
        _write_states(db, states)
        meta["state_hash"] = after
        meta["last_operation_id"] = operation_id
        _meta_write(db, meta)
        if fault:
            fault("before_commit")
        db.commit()
    if fault:
        fault("after_commit")
    return dict(result, operation_id=operation_id, before_hash=before,
                after_hash=after, idempotent=False)


def record_current_observation(path, observer, target, operation_id=None, fault=None):
    """Derive and record a public envelope from the current native snapshot."""
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        world, _, _, _ = storage._head(db)
        native_observation = world.observe_batch([observer])[0]
    envelope = public_envelope_from_native(native_observation, target)
    return record_observation(path, observer, native_observation, envelope,
                              operation_id=operation_id, fault=fault)


def save(path, destination):
    """Make a no-overwrite SQLite backup without changing the source world."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("F7 backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(storage._connect(path, readonly=True)) as source:
        with destination.open("xb"):
            pass
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("F7 backup integrity check failed")
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
        states = {(entry["observer"], entry["target"]): entry["state"]
                  for entry in meta["initial_inferences"]}
        operations = 0
        for operation_id, command_text, before, after, result_text in db.execute(
                "SELECT operation_id,command,before_hash,after_hash,result FROM f7_operations ORDER BY seq"):
            command = loads(command_text)
            if command["kind"] == "attach":
                if before != EMPTY_HASH or after != _state_hash(states):
                    raise ValueError("F7 attach replay mismatch")
                expected_result = {"event_count": 0, "changed": False}
            elif command["kind"] == "record_observation":
                if before != _state_hash(states):
                    raise ValueError("F7 operation chain mismatch")
                envelope = command["envelope"]
                key = (envelope["observer"], envelope["target"])
                if key not in states:
                    raise ValueError("F7 replay references unknown inference")
                expected_result = inference.infer(states[key], envelope)
                if after != _state_hash(states):
                    raise ValueError("F7 operation after hash mismatch")
            else:
                raise ValueError("unknown F7 operation")
            if dumps(expected_result) != result_text:
                raise ValueError("F7 operation result mismatch")
            operations += 1
        stored = _read_states(db, meta)
        actual = _state_hash(states)
        if actual != _state_hash(stored) or actual != meta["state_hash"]:
            raise ValueError("F7 final replay mismatch")
        return {"replay_matches": True, "operations": operations, "state_hash": actual}


__all__ = ["SCHEMA", "attach", "inspect", "public_envelope_from_native",
           "record_observation", "record_current_observation", "save", "resume", "replay"]
