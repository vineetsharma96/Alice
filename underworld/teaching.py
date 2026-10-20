"""Trusted operator mutation/branch channel. Never imported into a provider context."""
import copy
from pathlib import Path
import sqlite3
import re
import uuid

from . import storage, memory
from .config import validate,episodic_enabled
from .wire import dumps, loads


def intervene(path, request, fault=None):
    loads(dumps(request), 16384)
    db=storage._connect(path)
    try:
        db.execute("BEGIN IMMEDIATE")
        world,config,metadata,_=storage._head(db)
        if config["mode"]!="guided":raise ValueError("CLOSED_MODE: fork a guided branch for interventions")
        if type(request) is not dict or request.get("branch_id")!=metadata["branch_id"]:
            raise ValueError("UNAUTHORIZED: wrong branch")
        prior=db.execute("SELECT request,result FROM decisions WHERE source='operator' AND json_extract(request,'$.intervention_id')=?",
                         (request.get("intervention_id"),)).fetchone()
        if prior:
            if prior[0]!=dumps(request):raise ValueError("conflicting intervention id")
            return loads(prior[1])
        if db.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]>=storage.MAX_DECISIONS:
            raise ValueError("decision journal limit reached")
        result=world.intervene(request,"operator")
        events=world.step(0)  # Drain this transaction's events without advancing physical time.
        world.check_invariants()
        ids=[f"agent-{i+1}" for i in range(config["world"]["population"])]
        if memory.capture(db,world.observe_batch(ids),episodic_enabled(config)):memory.seal(db)
        state=world.checkpoint()
        if len(state.encode())>storage.MAX_CHECKPOINT_BYTES:raise ValueError("checkpoint size limit reached")
        state_hash=storage.head_hash(state,metadata["runtime_policy_state"])
        db.execute("INSERT INTO decisions(tick,request,result,source) VALUES(?,?,?,'operator')",
                   (int(world.snapshot()["tick"]),dumps(request),dumps(result)))
        db.executemany("INSERT INTO events VALUES(?,?,?)",[(int(e["seq"]),int(e["tick"]),dumps(e)) for e in events])
        if events:db.execute("DELETE FROM events WHERE seq<=?",(int(events[-1]["seq"])-config["logging"]["event_retention_count"],))
        db.execute("UPDATE run SET state=?,state_hash=? WHERE singleton=1",(state,state_hash))
        if fault:fault("before_commit")
        db.commit()
        if fault:fault("after_commit")
        return result
    except BaseException:
        db.rollback()
        raise
    finally:db.close()


def history(path):
    db=storage._connect(path,readonly=True)
    try:
        db.execute("BEGIN")
        _,_,metadata,_=storage._head(db)
        return {"branch_id":metadata["branch_id"],"laws_version":metadata["laws_version"],
                "parent_branch_id":metadata.get("parent_branch_id"),
                "interventions":[{"tick":r[0],"request":loads(r[1]),"result":loads(r[2])} for r in db.execute(
                    "SELECT tick,request,result FROM decisions WHERE source='operator' ORDER BY id LIMIT 256")]}
    finally:db.close()


def recall(path, agent, symbol):
    """Small experiment instrument: parse authored claim syntax in accessible original reports only.

    Unknown never becomes a guessed fact. Multiple contradictory claims are retained, not adjudicated.
    This is lexical recall, not a measure of general language understanding or spatial navigation.
    """
    if type(symbol) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",symbol):raise ValueError("invalid symbol")
    db=storage._connect(path,readonly=True)
    try:
        db.execute("BEGIN")
        storage._head(db)
        memory.private_view(db,agent)  # Validate the agent even when no claims exist.
        claims=[];omitted=0
        for row in db.execute("SELECT id,payload FROM episodes WHERE agent=? AND kind IN ('book_read','unverified_report') ORDER BY id DESC LIMIT 64",(agent,)):
            record=loads(row[1])
            for found,location in re.findall(r"FACT ([A-Za-z0-9_-]{1,64}) -> ([A-Za-z0-9_-]{1,64})(?=\s|$)",record.get("text","")):
                if found!=symbol:continue
                if len(claims)>=8:
                    omitted+=1
                    continue
                claims.append({"location":location,"episode_id":row[0],"observer_id":agent,
                    "source_id":record["source_id"],"origin_event_seq":record["origin_event_seq"],
                    "parent_event_seq":record["parent_event_seq"],"source_event_seq":record["source_event_seq"],
                    "delivery_tick":record["delivery_tick"],"speaker_id":record["speaker_id"],"confidence":"unverified"})
        return {"agent":agent,"symbol":symbol,"status":"reported" if claims else "unknown",
                "claims":claims,"omitted_claims":omitted,"engine_fact":False,"instrument":"bounded lexical report recall"}
    finally:db.close()


def fork(path, output, mode=None, hearing_range_m=None, episodic_memory=None):
    """Snapshot into a new branch; never changes the parent's time/config/laws/bytes."""
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("xb"):pass
    source=storage._connect(path,readonly=True)
    target=sqlite3.connect(output,isolation_level=None)
    try:
        source.execute("BEGIN")
        world,config,metadata,parent_hash=storage._head(source)
        parent_mental=memory.checksum(source)
        source.backup(target)
        config=copy.deepcopy(config)
        if mode is not None:config["mode"]=mode
        if hearing_range_m is not None:config["laws"]={"hearing_range_m":hearing_range_m}
        if episodic_memory is not None:
            if "culture" not in config:raise ValueError("episodic ablation requires a cultural experiment")
            config["culture"]["episodic_memory"]=episodic_memory
        validate(config)
        target.execute("PRAGMA synchronous=FULL")
        target.execute("BEGIN IMMEDIATE")
        world._configure_branch(config["mode"]=="guided",config.get("laws",{}).get("hearing_range_m",6))
        world.check_invariants()
        policy=metadata.pop("runtime_policy_state")
        state=world.checkpoint()
        metadata.update(branch_id=str(uuid.uuid4()),parent_branch_id=metadata["branch_id"],
            parent_run_id=world.snapshot()["run_id"],parent_state_hash=parent_hash,parent_cognitive_hash=parent_mental,
            parent_laws_version=metadata["laws_version"],laws_version=storage.laws_version(config),
            config_hash=storage.digest(dumps(config)),
            replay_after_id=target.execute("SELECT COALESCE(MAX(id),0) FROM decisions").fetchone()[0])
        hashed=storage.head_hash(state,policy)
        target.execute("UPDATE run SET config=?,metadata=?,state=?,state_hash=? WHERE singleton=1",
                       (dumps(config),dumps(metadata),state,hashed))
        tick=int(world.snapshot()["tick"])
        target.execute("DELETE FROM checkpoints")
        target.execute("INSERT INTO checkpoints VALUES('initial',?,?,?,?,?)",(tick,state,hashed,7,dumps(policy)))
        target.execute("DELETE FROM policy_frames")
        target.commit()
    except BaseException:
        target.rollback()
        raise
    finally:
        source.close();target.close()
    return storage.inspect(output)
