"""Bounded F12 integration of the native world and F8--F11 overlays.

F12 is deliberately a coordinator, not a new world implementation.  The
native SQLite head remains authoritative for identity, time, observations and
all physical actions.  This module copies a native world into a new database,
stores one private JSON state per actor, and records overlay-only operations in
one hash-chained journal.  No function in this module can mutate native state.
"""

from contextlib import closing
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3

from . import communication_f9 as communication
from . import identity_values_f11 as values
from . import regulation_f8 as regulation
from . import social_emotions_f10 as emotions
from . import storage


RULE = "alice-integration-f12-1"
SCHEMA = "alice-integration-store-f12-1"
MAX_OPERATIONS = 4096
TABLES = ("f12_meta", "f12_states", "f12_operations")
EMPTY_HASH = hashlib.sha256(b"{}").hexdigest()


def _dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _loads(text):
    return json.loads(text)


def _hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        raise FileExistsError("F12 attach requires a NEW destination")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as origin:
            with closing(sqlite3.connect(destination)) as target:
                origin.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("F12 destination backup integrity check failed")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if _file_hash(source) != source_hash:
        raise ValueError("source world changed during F12 attach")
    return source_hash


def _actors(world):
    return sorted(entity["entity_id"] for entity in world.snapshot()["entities"]
                   if entity.get("kind") == "actor")


def _validate_state(owner, state):
    if state.get("owner") != owner:
        raise ValueError("F12 overlay owner mismatch")
    regulation.validate(state["f8"])
    communication.validate(state["f9"])
    emotions.validate(state["f10"])
    values.validate(state["f11"])
    run_id=state['f8']['run_id']
    for key in ('f8','f9','f10','f11'):
        if state[key]['owner']!=owner or state[key]['run_id']!=run_id:
            raise ValueError('F12 embedded owner/run mismatch')


def _state_hash(states):
    rows = [{"owner": owner, "state": states[owner]} for owner in sorted(states)]
    return _hash_text(_dumps(rows))


def _initial_states(actors, run_id, declared_values):
    return {
        owner: {
            "owner": owner,
            "f8": regulation.initial(owner, run_id),
            "f9": communication.initial(owner, run_id),
            "f10": emotions.initial(owner, run_id),
            "f11": values.initial(owner, run_id, declared_values),
        }
        for owner in actors
    }


def _meta_read(db):
    row = db.execute("SELECT payload,checksum FROM f12_meta WHERE singleton=1").fetchone()
    if row is None or _hash_text(row[0]) != row[1]:
        raise ValueError("F12 metadata checksum mismatch")
    meta = _loads(row[0])
    if meta.get("schema") != SCHEMA or meta.get("rule") != RULE:
        raise ValueError("unsupported F12 integration schema")
    run_id = db.execute("SELECT run_id FROM run WHERE singleton=1").fetchone()[0]
    if meta.get("run_id") != run_id:
        raise ValueError("F12 run identity mismatch")
    if type(meta.get("actors")) is not list or meta["actors"] != sorted(meta["actors"]):
        raise ValueError("invalid F12 actor manifest")
    return meta


def _meta_write(db, meta):
    text = _dumps(meta)
    db.execute("UPDATE f12_meta SET payload=?,checksum=? WHERE singleton=1",
               (text, _hash_text(text)))


def _read_states(db, meta):
    states = {}
    for owner, payload, checksum in db.execute(
            "SELECT owner,payload,checksum FROM f12_states ORDER BY owner"):
        if _hash_text(payload) != checksum:
            raise ValueError("F12 overlay checksum mismatch")
        state = _loads(payload)
        _validate_state(owner, state)
        if state['f8']['run_id']!=meta['run_id']:
            raise ValueError('F12 embedded run identity mismatch')
        states[owner] = state
    if set(states) != set(meta["actors"]):
        raise ValueError("F12 overlay actor set is incomplete")
    if _state_hash(states) != meta["state_hash"]:
        raise ValueError("F12 overlay head hash mismatch")
    return states


def _write_states(db, states):
    for owner, state in states.items():
        text = _dumps(state)
        db.execute("UPDATE f12_states SET payload=?,checksum=? WHERE owner=?",
                   (text, _hash_text(text), owner))


def _owner(meta, owner):
    if type(owner) is not str or owner not in meta["actors"]:
        raise ValueError("unknown F12 actor")
    return owner


def _operation_id(request, operation_id):
    if operation_id is None:
        return "f12-op-" + _hash_text(_dumps(request))[:32]
    if type(operation_id) is not str or not 1 <= len(operation_id) <= 128:
        raise ValueError("invalid F12 operation ID")
    return operation_id


def _module_result(kind, states, request, current, interval=None):
    owner = request.get("owner")
    if kind=='observe_native_outcome':
        evidence=regulation.observe_outcome(states[owner]['f8'],interval['before'],interval['after'],interval['outcome'])
        return dict(owner=owner,evidence=evidence,evidence_provenance='native_journal_verified')
    if kind == "observe_current":
        evidence = regulation.observe_outcome(states[owner]["f8"], request["before"],
                                              current, request["outcome"])
        return {"owner": owner, "observation": deepcopy(current), "evidence": evidence}
    if kind == "send_signal":
        return communication.emit(states[owner]["f9"], request["meaning"],
                                  request["partner"], request["evidence_id"])
    if kind == "receive_signal":
        return communication.receive(states[owner]["f9"], request["speaker"],
                                     request["token"], request["evidence_id"])
    if kind == "feedback_signal":
        return communication.learn_from_feedback(
            states[owner]["f9"], request["token"], request["observed_meaning"],
            request["success"], request["evidence_id"], request["partner"])
    if kind == "observe_social":
        return emotions.observe_event(states[owner]["f10"], request["event"])
    if kind == "observe_current_social":
        return emotions.observe_event(states[owner]["f10"], request["event"])
    if kind == "revise_identity_event":
        return values.observe_event(states[owner]["f11"], request["event"])
    if kind == "revise_identity_summary":
        return values.revise_summary(states[owner]["f11"], request["summary"],
                                      request["evidence_id"])
    raise ValueError("unknown F12 operation")


def _stored_operation(db, operation_id, request, kind):
    row = db.execute(
        "SELECT command,result,before_hash,after_hash FROM f12_operations WHERE operation_id=?",
        (operation_id,)).fetchone()
    if row is None:
        return None
    command = _loads(row[0])
    if command.get("request") != request or command.get('kind')!=kind:
        raise ValueError("conflicting F12 operation identity")
    result = _loads(row[1])
    return dict(result, operation_id=operation_id, before_hash=row[2],
                after_hash=row[3], idempotent=True)


def _current(world, owner):
    current = world.observe_batch([owner])[0]
    if current.get("agent_id") != owner:
        raise ValueError("F12 native observation identity mismatch")
    return current


def _mutate(path, kind, request, operation_id=None):
    db = storage._connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        world, _, metadata, _ = storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        op_id = _operation_id(request, operation_id)
        existing = _stored_operation(db, op_id, request, kind)
        if existing is not None:
            db.commit()
            return existing
        owner = _owner(meta, request["owner"])
        current = _current(world, owner)
        before_hash = _state_hash(states)
        command = {"kind": kind, "request": deepcopy(request),
                   "native_observation": deepcopy(current)}
        interval=None
        if kind=='observe_native_outcome':
            from .native_intervals import action_intervals
            interval=action_intervals(db,owner,{request['request_id']}).get(request['request_id'])
            if interval is None:raise ValueError('No terminal own native action for F12 evidence')
            command['native_interval']=interval
        result = _module_result(kind, states, request, current,interval)
        after_hash = _state_hash(states)
        count = db.execute("SELECT COUNT(*) FROM f12_operations").fetchone()[0]
        if count >= MAX_OPERATIONS:
            raise ValueError("F12 operation journal limit reached")
        db.execute("INSERT INTO f12_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                   (op_id, _dumps(command), before_hash, after_hash, _dumps(result)))
        _write_states(db, states)
        meta["state_hash"] = after_hash
        meta["last_operation_id"] = op_id
        _meta_write(db, meta)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return dict(result, operation_id=op_id, before_hash=before_hash,
                after_hash=after_hash, idempotent=False)


def attach(source, destination, declared_values=None):
    """Copy ``source`` to a new database and initialize all four overlays."""
    if declared_values is None:
        declared_values = []
    if type(declared_values) not in (list, tuple):
        raise ValueError("F12 declared_values must be a bounded list")
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    source_hash = _copy_database(source, destination)
    source_after = _file_hash(source)
    try:
        with closing(storage._connect(destination)) as db:
            db.execute("BEGIN IMMEDIATE")
            world, _, metadata, native_hash = storage._head(db)
            if any(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                              (table,)).fetchone() for table in TABLES):
                raise ValueError("destination already contains F12 integration tables")
            actors = _actors(world)
            states = _initial_states(actors, metadata["branch_id"], declared_values)
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='f8_meta'").fetchone():
                from . import regulation_store_f8
                f8_meta=regulation_store_f8._meta_read(db)
                inherited=regulation_store_f8._read_states(db,f8_meta)
                if set(inherited)!=set(actors):raise ValueError('F12 inherited F8 actor mismatch')
                for owner in actors:states[owner]['f8']=deepcopy(inherited[owner])
            for owner, state in states.items():
                _validate_state(owner, state)
            overlay_hash = _state_hash(states)
            attach_id = "f12-attach-" + source_hash[:32]
            meta = {
                "schema": SCHEMA, "rule": RULE, "run_id": metadata["branch_id"],
                "actors": actors, "source_db_sha256": source_hash,
                "source_native_state_hash": native_hash,
                "native_schema": {"storage_db_version": storage.DB_VERSION,
                                  "checkpoint_schema": storage.CHECKPOINT_SCHEMA},
                "state_hash": overlay_hash, "last_operation_id": attach_id,
                "operation_quota": MAX_OPERATIONS,
                "initial_states": states,
            }
            db.executescript("""
                CREATE TABLE f12_meta(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f12_states(owner TEXT PRIMARY KEY,
                    payload TEXT NOT NULL, checksum TEXT NOT NULL);
                CREATE TABLE f12_operations(seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_id TEXT NOT NULL UNIQUE, command TEXT NOT NULL,
                    before_hash TEXT NOT NULL, after_hash TEXT NOT NULL, result TEXT NOT NULL);
                CREATE INDEX f12_operations_identity ON f12_operations(operation_id);
            """)
            meta_text = _dumps(meta)
            db.execute("INSERT INTO f12_meta VALUES(1,?,?)",
                       (meta_text, _hash_text(meta_text)))
            for owner, state in states.items():
                text = _dumps(state)
                db.execute("INSERT INTO f12_states VALUES(?,?,?)",
                           (owner, text, _hash_text(text)))
            command = {"kind": "attach", "request": {"source_db_sha256": source_hash,
                                                       "actors": actors}}
            db.execute("INSERT INTO f12_operations(operation_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)",
                       (attach_id, _dumps(command), EMPTY_HASH,
                        overlay_hash, _dumps({"event_count": 0, "changed": False})))
            db.commit()
    finally:
        if _file_hash(source) != source_after:
            raise ValueError("source world changed during F12 initialization")
    return inspect(destination)


def _summary(state):
    return {
        "f8": {"revision": state["f8"]["revision"],
               "evidence_count": len(state["f8"]["evidence"]),
               "failure_streaks": dict(state["f8"]["failure_streaks"])},
        "f9": {"revision": state["f9"]["revision"],
               "evidence_count": len(state["f9"]["evidence"]),
               "production_count": len(state["f9"]["production"]),
               "partner_count": len(state["f9"]["comprehension"])},
        "f10": {"revision": state["f10"]["revision"],
                "evidence_count": len(state["f10"]["evidence"]),
                "available": sorted(state["f10"]["states"])},
        "f11": {"revision": state["f11"]["revision"],
                "evidence_count": len(state["f11"]["evidence"]),
                "declared_value_count": len(state["f11"]["declared_values"]),
                "acquired_value_count": len(state["f11"]["acquired_preferences"]),
                "commitment_count": len(state["f11"]["commitments"]),
                "summary_evidence_count": len(state["f11"]["summary"]["evidence"])},
    }


def inspect(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        world, _, _, native_hash = storage._head(db)
        meta = _meta_read(db)
        states = _read_states(db, meta)
        snapshot = world.snapshot()
        return {
            "schema": SCHEMA, "rule": RULE, "run_id": meta["run_id"],
            "actors": list(meta["actors"]), "native_tick": int(snapshot["tick"]),
            "native_state_hash": native_hash, "source_db_sha256": meta["source_db_sha256"],
            "source_native_state_hash": meta["source_native_state_hash"],
            "native_schema": deepcopy(meta["native_schema"]),
            "state_hash": meta["state_hash"],
            "operation_count": db.execute("SELECT COUNT(*) FROM f12_operations").fetchone()[0],
            "overlay_summaries": {owner: _summary(states[owner]) for owner in meta["actors"]},
        }


def observe_current(path, owner, before=None, outcome=None, operation_id=None):
    """Read an own current observation and optionally learn one F8 outcome."""
    # A strict F10 public/native event may also be attached to this current
    # observation.  The dedicated observe_social API remains available when a
    # caller does not need the observation result in the same command.
    if outcome is not None and isinstance(outcome, dict) and "predicate" in outcome:
        if before is not None:
            raise ValueError("F12 social observation does not accept an F8 before snapshot")
        request = {"owner": owner, "event": deepcopy(outcome)}
        return _mutate(path, "observe_current_social", request, operation_id)
    if (before is None) != (outcome is None):
        raise ValueError("F12 F8 learning requires both before and outcome")
    if before is None:
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute("BEGIN")
            world, _, _, _ = storage._head(db)
            meta = _meta_read(db)
            _owner(meta, owner)
            states = _read_states(db, meta)
            current = _current(world, owner)
            return {"owner": owner, "observation": deepcopy(current),
                    "overlay_revision": states[owner]["f8"]["revision"]}
    request = {"owner": owner, "before": deepcopy(before), "outcome": deepcopy(outcome)}
    return _mutate(path, "observe_current", request, operation_id)


def send_signal(path, speaker, meaning, partner, evidence_id, operation_id=None):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        meta = _meta_read(db)
        _owner(meta, speaker)
        _owner(meta, partner)
        if speaker == partner:
            raise ValueError("F12 communication requires distinct actors")
    request = {"owner": speaker, "meaning": meaning, "partner": partner,
               "evidence_id": evidence_id}
    return _mutate(path, "send_signal", request, operation_id)


def record_native_outcome(path, owner, request_id, operation_id=None):
    """Learn from a real own terminal action, not a caller-shaped receipt."""
    if type(request_id) is not str or not 1<=len(request_id)<=128:
        raise ValueError('Invalid native request identity')
    return _mutate(path,'observe_native_outcome',dict(owner=owner,request_id=request_id),operation_id)


def receive_signal(path, receiver, speaker, token, evidence_id, operation_id=None):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        meta = _meta_read(db)
        _owner(meta, receiver)
        _owner(meta, speaker)
        if receiver == speaker:
            raise ValueError("F12 communication requires distinct actors")
    request = {"owner": receiver, "speaker": speaker, "token": token,
               "evidence_id": evidence_id}
    return _mutate(path, "receive_signal", request, operation_id)


def feedback_signal(path, receiver, token, observed_meaning, success, evidence_id,
                    partner, operation_id=None):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        meta = _meta_read(db)
        _owner(meta, receiver)
        _owner(meta, partner)
        if receiver == partner:
            raise ValueError("F12 communication requires distinct actors")
    request = {"owner": receiver, "token": token, "observed_meaning": observed_meaning,
               "success": success, "evidence_id": evidence_id, "partner": partner}
    return _mutate(path, "feedback_signal", request, operation_id)


def observe_social(path, owner, event, operation_id=None):
    if type(event) is not dict:
        raise ValueError("F12 social event must be a mapping")
    request = {"owner": owner, "event": deepcopy(event)}
    return _mutate(path, "observe_social", request, operation_id)


def revise_identity(path, owner, event_or_summary, operation_id=None):
    if type(event_or_summary) is not dict:
        raise ValueError("F12 identity revision must be a mapping")
    if "summary" in event_or_summary:
        request = {"owner": owner, "summary": deepcopy(event_or_summary["summary"],),
                   "evidence_id": event_or_summary.get("evidence_id")}
        if request["evidence_id"] is None:
            raise ValueError("F12 summary revision requires evidence_id")
        kind = "revise_identity_summary"
    else:
        request = {"owner": owner, "event": deepcopy(event_or_summary)}
        kind = "revise_identity_event"
    return _mutate(path, kind, request, operation_id)


def _choice_inputs(current, candidates):
    if type(candidates) is list:
        return {"f8": candidates}
    if type(candidates) is not dict:
        raise ValueError("F12 candidates must be a list or overlay mapping")
    allowed = {"f8", "f9", "f10", "f11"}
    if not set(candidates).issubset(allowed):
        raise ValueError("F12 candidates contain an unsupported overlay")
    return {key: candidates.get(key) for key in allowed if key in candidates}


def choose(path, owner, candidates):
    """Return overlay proposals without writing overlays or advancing native time."""
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        world, _, _, _ = storage._head(db)
        meta = _meta_read(db)
        _owner(meta, owner)
        states = _read_states(db, meta)
        current = _current(world, owner)
        inputs = _choice_inputs(current, candidates)
        result = {"owner": owner, "tick": int(current["tick"]),
                  "proposal_only": True, "choices": {}}
        if "f8" in inputs:
            result["choices"]["f8"] = regulation.choose(current, states[owner]["f8"], inputs["f8"])
        if "f9" in inputs:
            heard = current.get("heard")
            f9_observation = {"agent_id": owner, "run_id": meta["run_id"]}
            if heard is not None:
                f9_observation["heard"] = heard
            signals = current.get("signals")
            if signals is not None:
                f9_observation["signals"] = signals
            result["choices"]["f9"] = communication.choose_assistance(
                states[owner]["f9"], f9_observation, inputs["f9"])
        if "f10" in inputs:
            result["choices"]["f10"] = emotions.influence(states[owner]["f10"], inputs["f10"])
        if "f11" in inputs:
            context = current.get("context", [])
            result["choices"]["f11"] = values.choose_commitment_action(
                states[owner]["f11"], {"owner": owner, "run_id": meta["run_id"],
                                       "context": context}, inputs["f11"])
        return result


def _apply_replay(states, command, db=None):
    kind = command["kind"]
    request = command["request"]
    current = command.get("native_observation")
    interval=None
    if kind=='observe_native_outcome':
        from .native_intervals import action_intervals
        interval=action_intervals(db,request['owner'],{request['request_id']}).get(request['request_id'])
        if interval is None or _dumps(interval)!=_dumps(command.get('native_interval')):
            raise ValueError('F12 evidence differs from native action history')
    return _module_result(kind, states, request, current,interval)


def save(path, destination):
    """Create a no-overwrite SQLite backup of an attached F12 world."""
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError("F12 backup destination already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(storage._connect(path, readonly=True)) as source:
        with destination.open("xb"):
            pass
        try:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("F12 backup integrity check failed")
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return inspect(destination)


def replay(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute("BEGIN")
        storage._head(db)
        meta = _meta_read(db)
        states = deepcopy(meta["initial_states"])
        for owner, state in states.items():
            _validate_state(owner, state)
        operations = 0
        for _, operation_id, command_text, before, after, result_text in db.execute(
                "SELECT seq,operation_id,command,before_hash,after_hash,result FROM f12_operations ORDER BY seq"):
            command = _loads(command_text)
            if command["kind"] == "attach":
                if before != EMPTY_HASH:
                    raise ValueError("F12 attach operation chain mismatch")
                expected = {"event_count": 0, "changed": False}
                expected_after = _state_hash(states)
            else:
                if before != _state_hash(states):
                    raise ValueError("F12 operation chain mismatch")
                expected = _apply_replay(states, command,db)
                expected_after = _state_hash(states)
            if after != expected_after or _dumps(expected) != result_text:
                raise ValueError("F12 operation result or hash mismatch")
            operations += 1
        stored = _read_states(db, meta)
        actual = _state_hash(states)
        if actual != _state_hash(stored) or actual != meta["state_hash"]:
            raise ValueError("F12 final replay mismatch")
        return {"replay_matches": True, "operations": operations,
                "state_hash": actual, "last_operation_id": meta["last_operation_id"]}


def resume(path):
    result = inspect(path)
    result["replay"] = replay(path)
    return result


def manifest(path, wall_time_s=None):
    """Return a bounded evaluation manifest with explicit unverified gates."""
    if wall_time_s is not None and (type(wall_time_s) not in (int,float) or not math.isfinite(wall_time_s) or wall_time_s<0):
        raise ValueError('F12 wall time must be finite and nonnegative')
    result = inspect(path)
    summaries = result["overlay_summaries"]
    memory = {
        owner: {
            "f8_evidence": item["f8"]["evidence_count"],
            "f9_evidence": item["f9"]["evidence_count"],
            "f10_evidence": item["f10"]["evidence_count"],
            "f11_evidence": item["f11"]["evidence_count"],
        } for owner, item in summaries.items()
    }
    return {
        "rule": RULE, "schema": SCHEMA, "simulated_tick": result["native_tick"],
        "wall_time_s": wall_time_s, "operation_count": result["operation_count"],
        "overlay_memory": memory,
        "evidence_counts": {owner: sum(memory[owner].values()) for owner in memory},
        "unverified_gates": [
            "UW10W weather and F0-F5/H-profile integration",
            "native delivery/grounding of F9 signals",
            "caller-supplied social/identity evidence is not independently verified",
            "autonomous scheduler integration",
            "humanlike emotion or communication claim",
            "indefinite lifelong run",
            "scientific multi-seed F12 gate",
        ],
    }


__all__ = [
    "RULE", "SCHEMA", "MAX_OPERATIONS", "attach", "inspect", "observe_current",
    "send_signal", "receive_signal", "feedback_signal", "observe_social",
    "revise_identity", "choose", "save", "resume", "replay", "manifest", "record_native_outcome",
]
