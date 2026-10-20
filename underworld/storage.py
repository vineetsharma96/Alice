"""Single-writer, one-tick SQLite transactions. No simulation rules live here."""
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import uuid
import threading
import time
from datetime import datetime, timezone

from . import __version__
from .config import validate,episodic_enabled
from .native import load_native
from .wire import dumps, loads, counter
from .policy import choose
from . import memory, cognition
from .lease import Lease

DB_VERSION = 10
CHECKPOINT_SCHEMA = 9
INFERENCE_LOCK = threading.Lock()
MAX_DECISIONS = 10000
MAX_CHECKPOINT_BYTES = 8*1024*1024  # Same bound as native restore; never commit an unreadable head.


def digest(state):
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def head_hash(state,policy_state):
    return digest(state if not policy_state else state+"\n"+dumps(policy_state))


def orchestration_id():
    root = Path(__file__).parent
    return digest("".join((root / name).read_text(encoding="utf-8")
                          for name in ("storage.py", "wire.py", "config.py", "policy.py", "memory.py", "cognition.py", "resources.py", "teaching.py", "culture.py", "lab_policy.py", "runtime.py", "lease.py", "isolation.py", "supervisor.py", "worker.py")))


def laws_version(config):
    laws={"hearing_range_m":float(config.get("laws",{}).get("hearing_range_m",6))}
    laws["thermal"]=config.get("thermal",{"enabled":False})
    laws["ecology"]=config.get("ecology",{"enabled":False})
    laws["culture"]=config.get("culture",{"enabled":False})
    return "culture-6/"+digest(dumps(laws))[:12]


def _connect(path, readonly=False):
    path = Path(path).resolve()
    db = None
    if readonly:
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=10)
        db.execute("PRAGMA query_only=ON")
    else:
        if not path.is_file():
            raise ValueError("run database does not exist; use new")
        lease=Lease(path);lease.__enter__()
        try:
            db = sqlite3.connect(path, isolation_level=None, timeout=10,factory=WriterConnection)
            db.writer_lease=lease
        except BaseException:lease.__exit__(None,None,None);raise
    try:
        if not readonly:db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA user_version").fetchone()[0] != DB_VERSION:
            db.close();db = None
            raise ValueError("unsupported database version")
        if not readonly:
            row=db.execute("SELECT config FROM run WHERE singleton=1").fetchone()
            if row:
                cap=loads(row[0],65536).get("execution",{}).get("max_db_bytes")
                if cap:
                    pages=cap//db.execute("PRAGMA page_size").fetchone()[0]
                    if db.execute(f"PRAGMA max_page_count={pages}").fetchone()[0]>pages:
                        db.close();db = None;raise ValueError("database already exceeds configured disk quota")
    except BaseException:
        if db is not None:db.close()
        raise
    return db


class WriterConnection(sqlite3.Connection):
    def close(self):
        try:super().close()
        finally:
            if getattr(self,"writer_lease",None):self.writer_lease.__exit__(None,None,None);self.writer_lease=None


def _head(db):
    row = db.execute("SELECT run_id, config, metadata, state, state_hash, policy_state FROM run WHERE singleton=1").fetchone()
    if row is None:
        raise ValueError("missing run head")
    run_id, config_text, meta_text, state, state_hash, policy_text = row
    policy_state=loads(policy_text,65536)
    if head_hash(state,policy_state) != state_hash:
        raise ValueError("checkpoint checksum mismatch")
    config, metadata = loads(config_text, 65536), loads(meta_text, 65536)
    validate(config)
    from .runtime import verify_control
    verify_control(db)
    native = load_native()
    if metadata["build_id"] != native.build_id or metadata["orchestration_id"] != orchestration_id():
        raise ValueError("run build/runtime code mismatch; migration or original build required")
    if metadata["config_hash"] != digest(dumps(config)):
        raise ValueError("config checksum mismatch")
    memory.verify(db)
    world = native.World.restore(state, run_id)
    snapshot=world.snapshot()
    ecology=config.get("ecology",{})
    if snapshot["ecology"]["enabled"]!=ecology.get("enabled",False) or (ecology.get("enabled") and snapshot["ecology"]["forage_regeneration_kg_s"]!=ecology["regeneration_kg_s"]):
        raise ValueError("native/config ecology mismatch")
    thermal=config.get("thermal",{})
    culture=config.get("culture",{})
    if snapshot["culture"]["enabled"]!=culture.get("enabled",False) or (culture.get("enabled") and snapshot["culture"]["hidden_apparatus"]["seed"]!=str(culture["apparatus_seed"])):
        raise ValueError("native/config cultural apparatus mismatch")
    if snapshot["thermal"]["enabled"]!=thermal.get("enabled",False) or (thermal.get("enabled") and snapshot["thermal"]["open_boundaries"]!=thermal["open_boundaries"]):
        raise ValueError("native/config thermal mismatch")
    if snapshot["mode"]!=config["mode"] or snapshot["hearing_range_m"]!=config.get("laws",{}).get("hearing_range_m",6) or metadata["laws_version"]!=laws_version(config):
        raise ValueError("native/config law or mode mismatch; use explicit fork")
    metadata["runtime_policy_state"]=policy_state
    return world, config, metadata, state_hash


def create(path, config, scripted=True):
    validate(config)
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():raise FileExistsError(f"run already exists: {path}")
    native = load_native()
    run_id = str(uuid.uuid4())
    w = config["world"]
    agency=config.get("agency",{})
    bodies=agency.get("bodies_enabled",False)
    policy="utility" if scripted and agency.get("policy")=="utility" else "none"
    world = native.World(config["seed"], w["population"], w["width_m"], w["height_m"],
                         w["dt_s"], config["cognition"]["interval_ticks"], scripted and not bodies, run_id,
                         bodies,agency.get("food_kg",16),agency.get("water_kg",64),
                         agency.get("food_regen_kg_s",0),agency.get("water_regen_kg_s",0),
                         config["mode"]=="guided",config.get("laws",{}).get("hearing_range_m",6),
                         agency.get("tree_growth_kg_s",0))
    thermal=config.get("thermal",{})
    if thermal.get("enabled"):
        world.configure_thermal(thermal["open_boundaries"],thermal["water_kg"],thermal["fuel_kg"],thermal["oxygen_kg"],thermal["temperature_k"])
    if config.get("ecology",{}).get("enabled"):
        world.configure_ecology(config["ecology"]["forage_kg"],config["ecology"]["regeneration_kg_s"])
    if config.get("culture",{}).get("enabled"):
        world.configure_culture(config["culture"]["apparatus_seed"])
    state = world.checkpoint()
    metadata = {"schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "build_id": native.build_id, "orchestration_id": orchestration_id(),
                "config_hash": digest(dumps(config)), "scripted": scripted,
                "laws_version": laws_version(config), "package_version": __version__, "policy":policy,
                "commit_boundary": "one physical tick, cognition reservation/result, operator action or retention transaction", "parent_run_id": None,
                "branch_id":run_id,"replay_after_id":0}
    # Publish only after native/config validation; exclusive creation still wins races.
    with path.open("xb"):pass
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript(f"""
            BEGIN IMMEDIATE;
            CREATE TABLE run(singleton INTEGER PRIMARY KEY CHECK(singleton=1), run_id TEXT NOT NULL,
                config TEXT NOT NULL, metadata TEXT NOT NULL, state TEXT NOT NULL, state_hash TEXT NOT NULL,
                policy_state TEXT NOT NULL);
            CREATE TABLE events(seq INTEGER PRIMARY KEY, tick INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE decisions(id INTEGER PRIMARY KEY, tick INTEGER NOT NULL,
                request TEXT NOT NULL, result TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'external');
            CREATE INDEX decisions_tick ON decisions(tick,id);
            CREATE TABLE checkpoints(name TEXT PRIMARY KEY, tick INTEGER NOT NULL,
                state TEXT NOT NULL, state_hash TEXT NOT NULL, schema_version INTEGER NOT NULL, policy_state TEXT NOT NULL);
            CREATE TABLE policy_frames(tick INTEGER PRIMARY KEY, state TEXT NOT NULL);
            CREATE TABLE runtime_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload TEXT NOT NULL,checksum TEXT NOT NULL);
            CREATE TABLE runtime_epochs(epoch INTEGER PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE cognition_queue(agent TEXT PRIMARY KEY,due_tick INTEGER NOT NULL);
            PRAGMA user_version={DB_VERSION};
        """)
        # executescript commits the schema transaction; initialization is not published until a valid head exists.
        memory.initialize(db, config["seed"], w["population"])
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO run VALUES(1,?,?,?,?,?,?)", (run_id,dumps(config),dumps(metadata),state,digest(state),"{}"))
        db.execute("INSERT INTO checkpoints VALUES('initial',0,?,?,?,'{}')", (state,digest(state),CHECKPOINT_SCHEMA))
        runtime_payload=dumps({"epoch":0,"last_rotation_tick":0,"queue_dropped":0,"queue_served":0,"status":"ready"})
        db.execute("INSERT INTO runtime_state VALUES(1,?,?)",(runtime_payload,digest(runtime_payload+dumps([]))))
        db.commit()
    except BaseException:
        db.rollback()
        # Retain failed file for diagnosis; it has no valid head and cannot resume.
        raise
    finally:
        db.close()
    return inspect(path)


def snapshot_projection(db,world,metadata,state_hash):
    snapshot = world.snapshot()
    snapshot.update(config_hash=metadata["config_hash"], state_hash=state_hash,
                    branch_id=metadata["branch_id"],laws_version=metadata["laws_version"],
                    parent_branch_id=metadata.get("parent_branch_id"),
                    interventions=db.execute("SELECT COUNT(*) FROM decisions WHERE source='operator'").fetchone()[0],
                    retained_events=db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                    recorded_decisions=db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0],
                    cognitive_hash=memory.checksum(db),
                    cognition_calls=db.execute("SELECT COUNT(*) FROM cognition_calls").fetchone()[0],
                    episodes=db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])
    return snapshot


def inspect(path):
    db = _connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        world, config, metadata, state_hash = _head(db)
        return snapshot_projection(db,world,metadata,state_hash)
    finally:
        db.close()


def observe(path, agent_ids):
    db = _connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        world, _, _, _ = _head(db)
        return world.observe_batch(agent_ids)
    finally:
        db.close()


def recover(path):
    """Allow SQLite hot-journal recovery under a writer lock; no simulated time passes."""
    db = _connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        _head(db)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def read_decisions(path):
    decisions = []
    with Path(path).open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if len(decisions) >= MAX_DECISIONS:
                raise ValueError("too many decisions")
            item = loads(line)
            if type(item) is not dict or set(item) != {"at_tick", "request"} or type(item["request"]) is not dict:
                raise ValueError("decision line requires at_tick and request")
            decisions.append((counter(item["at_tick"]), item["request"]))
    return decisions


def mind(path, agent, query=""):
    """Privileged operator inspection. Providers receive only the selected agent's projection."""
    db = _connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        _,config,_,_=_head(db)
        return memory.private_view(db, agent, query,episodic_enabled(config))
    finally:
        db.close()


def think(path, agent, provider=None):
    """Pause logical time, infer without a SQLite writer lock, then compare-and-commit."""
    if not INFERENCE_LOCK.acquire(blocking=False):
        raise ValueError("inference concurrency limit reached")
    try:
        db = _connect(path, readonly=True)
        try:
            db.execute("BEGIN")
            world, config, _, state_hash = _head(db)
            observation = world.observe_batch([agent])[0]
            budget = config["cognition"]
            tick = int(observation["tick"])
            day = int(tick * config["world"]["dt_s"] // 86400)
            old_mental = memory.checksum(db)
            if db.execute("SELECT COUNT(*) FROM cognition_calls WHERE day=?", (day,)).fetchone()[0] >= budget["calls_per_simulated_day"]:
                return {"status": "quota", "tick": tick}
            if db.execute("SELECT COUNT(*) FROM cognition_calls").fetchone()[0] >= config.get("execution",{}).get("cognition_call_limit",1024):
                return {"status": "run_quota", "tick": tick}
            if observation["own_state"]["busy"] or not observation["own_state"]["alive"] or not observation["own_state"].get("present",True):
                return {"status": "busy_or_dead", "tick": tick}
            if provider is None:
                if budget["provider"] == "disabled":return {"status": "disabled", "tick": tick}
                provider = cognition.Baseline() if budget["provider"] == "baseline" else cognition.LlamaCpp()
            view = memory.private_view(db, agent, "book read report food water",episodic_enabled(config))
            context = cognition.context_for(observation, view)
            call_id = db.execute("SELECT COALESCE(MAX(id),0)+1 FROM cognition_calls").fetchone()[0]
        finally:
            db.close()
        # Reserve the attempt durably before inference. Crashes consume quota and leave an auditable
        # interrupted record; they cannot cause unlimited uncounted retries after restart.
        db = _connect(path)
        try:
            db.execute("BEGIN IMMEDIATE")
            _head(db)
            if db.execute("SELECT state_hash FROM run").fetchone()[0] != state_hash or memory.checksum(db) != old_mental:
                raise ValueError("run changed before inference reservation")
            pending = {"provider": type(provider).__name__, "context": context, "budget": budget,
                       "status": "interrupted_or_in_progress"}
            db.execute("INSERT INTO cognition_calls VALUES(?,?,?,?,?)", (call_id, agent, tick, day, dumps(pending)))
            memory.seal(db)
            old_mental = memory.checksum(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
        started = time.perf_counter()
        raw, details, error = "", {}, None
        evidence = [e["id"] for e in context["memories"]]
        provenance_refs={e["id"]:e["source_event_seq"] for e in context["memories"] if "source_event_seq" in e}
        try:
            raw, details, _ = cognition.bounded_call(provider, context, budget)
            plan, _ = cognition.compile_plan(raw, observation, evidence, call_id, provenance_refs)
        except (ValueError, OSError, TimeoutError, EOFError, RuntimeError) as failure:
            error = type(failure).__name__ + ": " + str(failure)[:240]
            fallback, _ = cognition.Baseline().generate(context, budget)
            plan, _ = cognition.compile_plan(fallback, observation, evidence, call_id, provenance_refs)
        chosen = dumps(plan)
        elapsed = time.perf_counter() - started
        record = {"provider": type(provider).__name__, "context": context, "budget": budget,
                  "raw": raw, "details": details, "error": error, "latency_s": elapsed,
                  "status": "fallback" if error else "planned", "plan": plan}
        db = _connect(path)
        try:
            db.execute("BEGIN IMMEDIATE")
            _head(db)
            if db.execute("SELECT state_hash FROM run").fetchone()[0] != state_hash or memory.checksum(db) != old_mental:
                raise ValueError("run changed during inference; discarded stale completion")
            db.execute("UPDATE cognition_calls SET payload=? WHERE id=?", (dumps(record), call_id))
            if episodic_enabled(config):
                memory.episode(db, agent, f"perception:{call_id}", tick, "perception", context["perception"])
                memory.episode(db, agent, f"belief:{call_id}", tick, "derived_belief",
                    {"text": plan["interpretation"], "confidence": "unverified inference", "evidence": plan["evidence"],
                     "perception_source": f"perception:{call_id}", "provider": type(provider).__name__})
            stored = {"raw": chosen, "call_id": call_id, "evidence": evidence,"provenance_refs":provenance_refs,
                      "created_tick": tick, "expires_tick": tick + 100, "status": "pending"}
            db.execute("INSERT OR REPLACE INTO plans VALUES(?,?)", (agent, dumps(stored)))
            memory.seal(db)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
        return {"call_id": call_id, "agent": agent, "tick": tick, "status": record["status"],
                "plan": plan, "error": error, "latency_s": elapsed}
    finally:
        INFERENCE_LOCK.release()


def advance(path, ticks, decisions=(), fault=None):
    if type(ticks) is not int or not 1 <= ticks <= 100000:
        raise ValueError("advance ticks must be integer in [1,100000]")
    db = _connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        world, config, metadata, _ = _head(db)
        start = int(world.snapshot()["tick"])
    finally:
        db.close()
    decisions=tuple(decisions)  # Validation must not consume one-shot external action iterators.
    if config["cognition"]["provider"] == "disabled" or not metadata["scripted"]:
        return _advance(path, ticks, decisions, fault)
    if any(type(t) is not int or not start <= t < start+ticks for t, _ in decisions):
        raise ValueError("decision tick outside this advance interval")
    current, end = start, start + ticks
    interval = config["cognition"]["interval_ticks"]
    while current < end:
        if current % interval == 0:
            agent = f"agent-{(current // interval) % config['world']['population']+1}"
            think(path, agent)
        count = min(end-current, interval-current % interval)
        result = _advance(path, count, [(t,r) for t,r in decisions if current<=t<current+count], fault)
        current += count
    return result


def _advance(path, ticks, decisions=(), fault=None, stop_requested=None):
    if type(ticks) is not int or not 1 <= ticks <= 100000:
        raise ValueError("advance ticks must be integer in [1,100000]")
    # Repeated calls can reach the explicit Phase 1 run guard, not an unbounded loop.
    db = _connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        world, config, metadata, state_hash = _head(db)
        policy_state=metadata["runtime_policy_state"]
        start = int(world.snapshot()["tick"])
        if start + ticks > 1000000:
            raise ValueError("Phase 1 run limit is 1,000,000 ticks")
        by_tick = {}
        for at_tick, request in decisions:
            if type(at_tick) is not int or not start <= at_tick < start+ticks:
                raise ValueError("decision tick outside this advance interval")
            loads(dumps(request), config["logging"]["max_payload_bytes"])
            by_tick.setdefault(at_tick, []).append(request)
        decision_count=db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        if decision_count + sum(map(len,by_tick.values())) > MAX_DECISIONS:
            raise ValueError("decision journal limit reached")
        for offset in range(ticks):
            if stop_requested and stop_requested():break
            if offset:
                db.execute("BEGIN IMMEDIATE")
                # A second writer might advance between transactions. Never overwrite it.
                current = db.execute("SELECT state_hash FROM run WHERE singleton=1").fetchone()[0]
                if current != state_hash:
                    raise ValueError("concurrent writer advanced run; retry from committed head")
            tick = start+offset
            for request in by_tick.get(tick, []):
                result = world.submit(request, request.get("agent_id", ""))
                db.execute("INSERT INTO decisions(tick,request,result,source) VALUES(?,?,?,'external')", (tick,dumps(request),dumps(result)))
                decision_count+=1
            mental_changed = False
            # One-step plans enter the same native validation and physical journal as utility actions.
            for agent_id, payload in db.execute("SELECT agent,payload FROM plans ORDER BY agent").fetchall():
                plan = loads(payload)
                if plan["status"] != "pending":continue
                observation = world.observe_batch([agent_id])[0]
                own = observation["own_state"]
                body = own.get("body", {})
                urgent = any(body.get(k,0)>=v for k,v in (("hunger",.5),("thirst",.5),("fatigue",.55)))
                if own["busy"] or urgent or tick > plan["expires_tick"] or not own["alive"] or not own.get("present",True):
                    plan["status"] = "preempted"
                else:
                    if decision_count>=MAX_DECISIONS:raise ValueError("decision journal limit reached")
                    try:
                        _, request = cognition.compile_plan(plan["raw"], observation, plan["evidence"], plan["call_id"],
                            {int(k):v for k,v in plan.get("provenance_refs",{}).items()})
                        result = world.submit(request, agent_id)
                        db.execute("INSERT INTO decisions(tick,request,result,source) VALUES(?,?,?,'cognition')",
                                   (tick,dumps(request),dumps(result)))
                        decision_count += 1
                        plan["status"] = result["status"]
                        plan["request_id"] = request["request_id"]
                    except ValueError as error:
                        plan["status"], plan["error"] = "invalidated", str(error)
                db.execute("UPDATE plans SET payload=? WHERE agent=?", (dumps(plan),agent_id))
                mental_changed = True
            if metadata["policy"]=="utility" and tick%config["agency"]["interval_ticks"]==0:
                ids=[f"agent-{i+1}" for i in range(config["world"]["population"])]
                for observation in world.observe_batch(ids):
                    agent_id=observation["agent_id"]
                    action=choose(observation,policy_state.setdefault(agent_id,{}))
                    if action is not None:
                        if decision_count>=MAX_DECISIONS:raise ValueError("decision journal limit reached")
                        loads(dumps(action),config["logging"]["max_payload_bytes"])
                        result=world.submit(action,agent_id)
                        db.execute("INSERT INTO decisions(tick,request,result,source) VALUES(?,?,?,'utility')",
                                   (tick,dumps(action),dumps(result)))
                        decision_count+=1
                db.execute("INSERT INTO policy_frames VALUES(?,?)",(tick,dumps(policy_state)))
            events = world.step(1)
            ids=[f"agent-{i+1}" for i in range(config["world"]["population"])]
            mental_changed |= memory.capture(db, world.observe_batch(ids),episodic_enabled(config))
            if mental_changed:memory.seal(db)
            # Invariants are checked in native code before a tick can be persisted.
            world.check_invariants()
            state = world.checkpoint()
            if len(state.encode("utf-8"))>MAX_CHECKPOINT_BYTES:
                raise ValueError("checkpoint size limit reached; tick was not committed")
            state_hash = head_hash(state,policy_state)
            db.executemany("INSERT INTO events VALUES(?,?,?)",
                           [(int(e["seq"]), int(e["tick"]), dumps(e)) for e in events])
            seq = int(events[-1]["seq"])
            db.execute("DELETE FROM events WHERE seq<=?", (seq-config["logging"]["event_retention_count"],))
            db.execute("UPDATE run SET state=?,state_hash=?,policy_state=? WHERE singleton=1", (state,state_hash,dumps(policy_state)))
            if fault:
                fault("before_commit", tick+1)
            db.commit()
            if fault:
                fault("after_commit", tick+1)
    except BaseException:
        db.rollback()
        # No caller receives the staged world after a failed transaction.
        raise
    finally:
        db.close()
    return inspect(path)


def save(path, name, output=None, _automated=False):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name) or name == "initial":
        raise ValueError("invalid/reserved checkpoint name")
    if name.startswith("auto_epoch_") and not _automated:raise ValueError("reserved unattended checkpoint namespace")
    db = _connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        world, _, metadata, state_hash = _head(db)
        if db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] >= 16:
            raise ValueError("checkpoint limit reached (16 including initial)")
        db.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?)",
                   (name,int(world.snapshot()["tick"]),world.checkpoint(),state_hash,CHECKPOINT_SCHEMA,dumps(metadata["runtime_policy_state"])))
        db.commit()
        if output is not None:
            output = Path(output).resolve()
            if output.exists():
                raise FileExistsError("backup destination already exists")
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_name(output.name+".tmp-"+uuid.uuid4().hex)
            try:
                target = sqlite3.connect(temporary)
                try:
                    db.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("backup integrity check failed")
                finally:
                    target.close()
                with temporary.open("r+b") as stream:
                    os.fsync(stream.fileno())
                # Atomic no-overwrite publication on the same filesystem.
                os.link(temporary, output)
            finally:
                temporary.unlink(missing_ok=True)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
    return {"checkpoint":name,"state_hash":state_hash,"backup":str(output) if output else None}


def replay(path):
    db = _connect(path, readonly=True)
    try:
        db.execute("BEGIN")
        head, _, metadata, expected = _head(db)
        row = db.execute("SELECT state,state_hash,policy_state,tick FROM checkpoints WHERE name='initial'").fetchone()
        if row is None or head_hash(row[0],loads(row[2],65536)) != row[1]:
            raise ValueError("initial checkpoint checksum mismatch")
        world = load_native().World.restore(row[0], head.snapshot()["run_id"])
        decisions = iter(db.execute("SELECT tick,request,result,source FROM decisions WHERE id>? ORDER BY tick,id",(metadata.get("replay_after_id",0),)))
        item = next(decisions, None)
        frames=iter(db.execute("SELECT tick,state FROM policy_frames WHERE tick>=? ORDER BY tick",(row[3],)))
        frame=next(frames,None)
        policy_state=loads(row[2],65536)
        for tick in range(row[3],int(head.snapshot()["tick"])+1):
            while item is not None and item[0] == tick:
                request = loads(item[1])
                if item[3]=="operator":
                    result=world.intervene(request,"operator")
                    world.step(0)
                else:result = world.submit(request, request["agent_id"])
                if dumps(result) != item[2]:
                    raise ValueError(f"decision result diverged at tick {tick}")
                item = next(decisions, None)
            if tick<int(head.snapshot()["tick"]):world.step(1)
            if frame is not None and frame[0]==tick:
                policy_state=loads(frame[1],65536)
                frame=next(frames,None)
        if item is not None:
            raise ValueError("decision journal contains future decisions")
        if frame is not None:raise ValueError("policy journal contains future frames")
        actual = head_hash(world.checkpoint(),policy_state)
        if actual != expected:
            raise ValueError("replay state hash mismatch")
        return {"replay_matches":True,"tick":head.snapshot()["tick"],"state_hash":actual}
    finally:
        db.close()
