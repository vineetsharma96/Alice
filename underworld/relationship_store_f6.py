"""Durable, copy-only F6 relationship overlay for existing general worlds.

The native world and the historical storage journal remain unchanged.  F6 adds
tables to a copied SQLite database, and records only directional estimates
derived from native-shaped social reports or completed native receipts.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from . import relationships_f6 as relationships
from . import storage
from .lease import Lease
from .wire import dumps, loads


SCHEMA = "alice-relationship-store-f6-1"
MAX_OPERATIONS = 25000
EMPTY_HASH = hashlib.sha256(b"{}").hexdigest()
TABLES = ("f6_meta", "f6_relationships", "f6_operations")


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _db_connect(path, readonly=True):
    path = Path(path).resolve()
    if readonly:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None)
        db.execute("PRAGMA query_only=ON")
    else:
        db = sqlite3.connect(path, isolation_level=None)
    db.execute("PRAGMA foreign_keys=ON")
    return db


def _copy_database(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if not source.is_file():
        raise ValueError("source world does not exist")
    if destination.exists():
        raise FileExistsError("F6 attach requires a NEW destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
            with closing(sqlite3.connect(destination)) as target:
                origin.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("F6 destination backup integrity check failed")
    except BaseException:
        raise
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed during F6 attach")
    return source_hash


def _meta_read(db):
    row = db.execute("SELECT payload,checksum FROM f6_meta WHERE singleton=1").fetchone()
    if row is None or hashlib.sha256(row[0].encode("utf-8")).hexdigest() != row[1]:
        raise ValueError("F6 metadata checksum mismatch")
    meta = loads(row[0])
    if meta.get("schema") != SCHEMA:
        raise ValueError("unsupported F6 relationship schema")
    run_id = db.execute("SELECT run_id FROM run WHERE singleton=1").fetchone()[0]
    if meta.get("run_id") != run_id:
        raise ValueError("F6 run identity mismatch")
    return meta


def _meta_write(db, meta):
    text = dumps(meta)
    db.execute("UPDATE f6_meta SET payload=?,checksum=? WHERE singleton=1",
               (text, hashlib.sha256(text.encode("utf-8")).hexdigest()))


def _state_hash(states):
    rows = [{"owner": owner, "other": other, "state": states[(owner, other)]}
            for owner, other in sorted(states)]
    return hashlib.sha256(dumps(rows).encode("utf-8")).hexdigest()


def _actors(world):
    return sorted(entity["entity_id"] for entity in world.snapshot()["entities"]
                   if entity.get("kind") == "actor")


def _initial_states(actors):
    return {(owner, other): relationships.initial(owner, other)
            for owner in actors for other in actors if owner != other}


def _read_states(db, meta):
    states = {}
    for owner, other, payload, checksum in db.execute(
            "SELECT owner,other,payload,checksum FROM f6_relationships ORDER BY owner,other"):
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != checksum:
            raise ValueError("F6 relationship checksum mismatch")
        state = loads(payload)
        if state.get("owner") != owner or state.get("other") != other:
            raise ValueError("F6 relationship identity mismatch")
        relationships.validate(state)
        states[(owner, other)] = state
    expected = set((owner, other) for owner in meta["actors"] for other in meta["actors"]
                   if owner != other)
    if set(states) != expected:
        raise ValueError("F6 directional relationship set is incomplete")
    if _state_hash(states) != meta["state_hash"]:
        raise ValueError("F6 relationship head hash mismatch")
    return states


def _write_states(db, states):
    for (owner, other), state in states.items():
        text = dumps(state)
        db.execute("UPDATE f6_relationships SET payload=?,checksum=? WHERE owner=? AND other=?",
                   (text, hashlib.sha256(text.encode("utf-8")).hexdigest(), owner, other))


def _int_tick(value, label):
    if type(value) is int and value >= 0:
        return value
    if type(value) is str and value.isdigit():
        return int(value)
    raise ValueError(f"invalid F6 {label}")


def _native_social_event(observer, report):
    if type(report) is not dict or set(report) != {"source_event_seq", "tick", "other", "kind"}:
        raise ValueError("F6 social reports must contain only native witnessed fields")
    if type(report["source_event_seq"]) not in (str, int) or not str(report["source_event_seq"]):
        raise ValueError("invalid F6 social report identity")
    if type(report["other"]) is not str or not report["other"]:
        raise ValueError("invalid F6 social report target")
    return {"observer": observer, "other": report["other"], "kind": report["kind"],
            "source_event_seq": str(report["source_event_seq"]),
            "tick": _int_tick(report["tick"], "social report tick")}


def _decision_for_receipt(db, request_id):
    for (text,) in db.execute("SELECT request FROM decisions ORDER BY id"):
        request = loads(text)
        if request.get("request_id") == request_id:
            return request
    return None


def _receipt_events(db, observer, observation, actors):
    events = []
    for receipt in observation.get("recent_action_results", []):
        if type(receipt) is not dict or receipt.get("status") != "completed":
            continue
        request_id = receipt.get("request_id")
        request = _decision_for_receipt(db, request_id) if type(request_id) is str else None
        if request is None or request.get("agent_id") != observer:
            continue
        action = request.get("action_type")
        kind = {"give": "resource_given", "offer_task": "task_offered"}.get(action)
        other = None
        if action == "respond_task":
            accepted = request.get("parameters", {}).get("accept")
            agreement_id = request.get("parameters", {}).get("agreement_id")
            offers = observation.get("task_offers", [])
            offer = next((item for item in offers
                          if isinstance(item, dict) and item.get("id") == agreement_id), None)
            if type(accepted) is bool and offer is not None and offer.get("proposer") in actors:
                kind = "task_accepted" if accepted else "task_declined"
                other = offer["proposer"]
        if kind is None:
            continue
        targets = request.get("target_ids")
        if other is None:
            if type(targets) is not list or len(targets) != 1 or targets[0] not in actors:
                continue
            other = targets[0]
        refs = receipt.get("event_refs")
        if type(refs) is not list or not refs:
            raise ValueError("completed native receipt has no event reference")
        events.append({"observer": observer, "other": other, "kind": kind,
                       "source_event_seq": str(refs[-1]),
                       "tick": _int_tick(receipt.get("completed_tick", observation.get("tick", 0)),
                                          "receipt tick")})
    return events


def _events_from_observation(db, observation, actors):
    if type(observation) is not dict or type(observation.get("agent_id")) is not str:
        raise ValueError("F6 requires a native observation")
    observer = observation["agent_id"]
    if observer not in actors:
        raise ValueError("unknown F6 observer")
    if type(observation.get("social_reports", [])) is not list or type(observation.get("recent_action_results", [])) is not list:
        raise ValueError("F6 native observation report lists are invalid")
    events = [_native_social_event(observer, report)
              for report in observation.get("social_reports", [])]
    events.extend(_receipt_events(db, observer, observation, actors))
    return events


def _command_events(events, actors):
    if type(events) is not list or len(events) > 64:
        raise ValueError("F6 event batch is too large")
    normalized = []
    for event in events:
        if type(event) is not dict or set(event) != {"observer", "other", "kind", "source_event_seq", "tick"}:
            raise ValueError("F6 events must not contain observer labels or private target state")
        if (type(event["observer"]) is not str or type(event["other"]) is not str or
                type(event["source_event_seq"]) is not str or not event["source_event_seq"]):
            raise ValueError("invalid F6 event identity")
        if event["kind"] not in relationships.KINDS:
            raise ValueError("invalid F6 event kind")
        if event["observer"] not in actors or event["other"] not in actors:
            raise ValueError("F6 event references unknown inhabitant")
        relationships.validate(relationships.initial(event["observer"], event["other"]))
        normalized.append({"observer": event["observer"], "other": event["other"],
                           "kind": event["kind"], "source_event_seq": event["source_event_seq"],
                           "tick": _int_tick(event["tick"], "event tick")})
    return sorted(normalized, key=lambda event: (event["observer"], event["other"],
                                                   event["source_event_seq"], event["kind"], event["tick"]))


def _apply_events(states, events):
    changed = []
    for event in events:
        evidence = relationships.observe(states[(event["observer"], event["other"])], event)
        if evidence is not None:
            changed.append({"event": event, "evidence": evidence})
    return changed


def _operation_id(command, operation_id):
    if operation_id is None:
        return "f6-op-" + hashlib.sha256(dumps(command).encode("utf-8")).hexdigest()[:32]
    if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
        raise ValueError("invalid F6 operation ID")
    return operation_id


def _commit_events(db, meta, events, operation_id=None, fault=None):
    events = _command_events(events, meta["actors"])
    command = {"kind": "record_events", "events": events}
    operation_id = _operation_id(command, operation_id)
    old = db.execute("SELECT operation_id,command,result,before_hash,after_hash FROM f6_operations WHERE operation_id=?",
                     (operation_id,)).fetchone()
    if old:
        if old[1] != dumps(command):
            raise ValueError("conflicting F6 operation identity")
        return dict(loads(old[2]), operation_id=operation_id, before_hash=old[3],
                    after_hash=old[4], idempotent=True)
    if db.execute("SELECT COUNT(*) FROM f6_operations").fetchone()[0] >= MAX_OPERATIONS:
        raise ValueError("F6 operation journal limit reached")
    states = _read_states(db, meta)
    before = _state_hash(states)
    changed = _apply_events(states, events)
    after = _state_hash(states)
    result = {"changed": changed, "event_count": len(events)}
    db.execute("INSERT INTO f6_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
               (operation_id, dumps(command), before, after, dumps(result)))
    _write_states(db, states)
    meta["state_hash"] = after
    meta["last_operation_id"] = operation_id
    _meta_write(db, meta)
    if fault:
        fault("before_commit")
    return dict(result, operation_id=operation_id, before_hash=before, after_hash=after, idempotent=False)


def attach(source, destination, agents=None):
    """Copy an existing general world, then initialize only additive F6 tables."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    source_hash = _copy_database(source, destination)
    source_after = _file_hash(source)
    try:
        with Lease(destination), closing(storage._connect(destination)) as db:
            db.execute("BEGIN IMMEDIATE")
            storage._head(db)
            if any(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                   for table in TABLES):
                raise ValueError("destination already contains F6 relationship tables")
            world, _, metadata, _ = storage._head(db)
            all_actors = _actors(world)
            selected = all_actors if agents is None else sorted(set(agents))
            if selected != all_actors:
                raise ValueError("F6 attach initializes every actor pair in the copied world")
            states = _initial_states(all_actors)
            state_hash = _state_hash(states)
            meta = {"schema": SCHEMA, "run_id": metadata["branch_id"], "actors": all_actors,
                    "source_db_sha256": source_hash, "state_hash": state_hash,
                    "last_operation_id": None,
                    "initial_relationships": [{"owner": owner, "other": other,
                                               "state": states[(owner, other)]}
                                              for owner, other in sorted(states)]}
            db.executescript("""
                CREATE TABLE f6_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f6_relationships(owner TEXT NOT NULL, other TEXT NOT NULL,
                    payload TEXT NOT NULL, checksum TEXT NOT NULL,
                    PRIMARY KEY(owner,other));
                CREATE TABLE f6_operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE, command TEXT NOT NULL,
                    before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, result TEXT NOT NULL);
                CREATE INDEX f6_operations_identity ON f6_operations(operation_id);
            """)
            meta_text = dumps(meta)
            db.execute("INSERT INTO f6_meta VALUES(1,?,?)",
                       (meta_text, hashlib.sha256(meta_text.encode("utf-8")).hexdigest()))
            for (owner, other), state in states.items():
                text = dumps(state)
                db.execute("INSERT INTO f6_relationships VALUES(?,?,?,?)",
                           (owner, other, text, hashlib.sha256(text.encode("utf-8")).hexdigest()))
            command = {"kind": "attach", "source_db_sha256": source_hash, "actors": all_actors}
            db.execute("INSERT INTO f6_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                       ("f6-attach-" + source_hash[:32], dumps(command), EMPTY_HASH, state_hash,
                        dumps({"event_count": 0, "changed": []})))
            db.commit()
    finally:
        if source_after != source_hash:
            raise ValueError("source world changed during F6 initialization")
    return inspect(destination)


def inspect(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        return {"schema": SCHEMA, "run_id": meta["run_id"], "actors": list(meta["actors"]),
                "state_hash": meta["state_hash"], "source_db_sha256": meta["source_db_sha256"],
                "operation_count": db.execute("SELECT COUNT(*) FROM f6_operations").fetchone()[0],
                "relationships": {f"{owner}->{other}": state for (owner, other), state in states.items()}}


def record_events(path, events, operation_id=None, fault=None):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        storage._head(db)
        meta = _meta_read(db)
        result = _commit_events(db, meta, events, operation_id, fault)
        db.commit()
    if fault:
        fault("after_commit")
    return result


def record_observation(path, observer, observation=None, fault=None):
    """Record only the observer's native social reports and completed own receipts."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute("BEGIN IMMEDIATE")
        world, _, _, _ = storage._head(db)
        meta = _meta_read(db)
        native_observation = world.observe_batch([observer])[0]
        if observation is not None and observation != native_observation:
            raise ValueError("F6 observation must match the current native observation")
        observation = native_observation
        if observation.get("agent_id") != observer:
            raise ValueError("F6 observation identity mismatch")
        events = _events_from_observation(db, observation, meta["actors"])
        result = _commit_events(db, meta, events, fault=fault)
        db.commit()
    if fault:
        fault("after_commit")
    return result


def choose_helper(path, observer, candidates):
    """Rank only currently visible actor candidates; native validation stays authoritative."""
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        world, _, _, _ = storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        observation = world.observe_batch([observer])[0]
        visible = {entity["entity_id"] for entity in observation["visible_entities"]
                   if entity.get("kind") == "actor"}
        scoped = {other: state for (owner, other), state in states.items() if owner == observer}
        return relationships.choose_helper(scoped, [candidate for candidate in candidates if candidate in visible])


def save(path, destination):
    """Make a no-overwrite SQLite backup without changing the source world."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("F6 backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Lease(path), closing(storage._connect(path, readonly=True)) as source:
        with destination.open("xb"):
            pass
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("F6 backup integrity check failed")
    return inspect(destination)


def resume(path):
    """Validate a copied world and its F6 journal before continuing work."""
    result = inspect(path)
    result["replay"] = replay(path)
    return result


def replay(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = {(entry["owner"], entry["other"]): entry["state"]
                  for entry in meta["initial_relationships"]}
        if _state_hash(states) != meta["state_hash"] and not db.execute(
                "SELECT 1 FROM f6_operations WHERE seq=1 AND before_hash=?", (EMPTY_HASH,)).fetchone():
            raise ValueError("F6 initial relationship checksum mismatch")
        operations = 0
        for operation_id, command_text, before, after, result_text in db.execute(
                "SELECT operation_id,command,before_hash,after_hash,result FROM f6_operations ORDER BY seq"):
            command = loads(command_text)
            if command["kind"] == "attach":
                if before != EMPTY_HASH or after != _state_hash(states):
                    raise ValueError("F6 attach replay mismatch")
            elif command["kind"] == "record_events":
                if before != _state_hash(states):
                    raise ValueError("F6 operation chain mismatch")
                changed = _apply_events(states, _command_events(command["events"], meta["actors"]))
                if dumps({"changed": changed, "event_count": len(command["events"])}) != result_text:
                    raise ValueError("F6 operation result mismatch")
                if after != _state_hash(states):
                    raise ValueError("F6 operation after hash mismatch")
            else:
                raise ValueError("unknown F6 operation")
            operations += 1
        actual = _state_hash(states)
        stored = _read_states(db, meta)
        if actual != _state_hash(stored) or actual != meta["state_hash"]:
            raise ValueError("F6 final replay mismatch")
        return {"replay_matches": True, "operations": operations, "state_hash": actual}
