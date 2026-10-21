"""Bounded single-writer supervision; physical ticks still commit individually."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import shutil
import threading
import time
import uuid

from . import storage,memory
from .lease import Lease
from .resources import process_memory
from .wire import dumps,loads

DEFAULTS={"batch_ticks":50,"epoch_ticks":500,"checkpoint_keep":3,"max_db_bytes":33554432,
    "max_archive_bytes":134217728,"metrics_keep":128,"memory_recent":16,"queue_limit":64,
    "calls_per_batch":1,"cognition_call_limit":128,"episodic_memory":True}


def verify_control(db):
    row=db.execute("SELECT payload,checksum FROM runtime_state WHERE singleton=1").fetchone()
    queue=db.execute("SELECT agent,due_tick FROM cognition_queue ORDER BY agent").fetchall()
    if not row or storage.digest(row[0]+dumps(queue))!=row[1]:raise ValueError("runtime control checksum mismatch")
    control=loads(row[0],65536);previous=None;latest=None
    for number,payload in db.execute("SELECT epoch,payload FROM runtime_epochs ORDER BY epoch"):
        record=loads(payload,65536);hashed=record.pop("chain_hash")
        if record["epoch"]!=number or storage.digest(dumps(record))!=hashed or (previous is not None and record["previous_chain"]!=previous):raise ValueError("runtime epoch chain mismatch")
        previous=hashed;latest=number
    if (control["epoch"] and (latest!=control["epoch"] or previous!=control.get("chain_head"))) or (not control["epoch"] and latest is not None):raise ValueError("runtime epoch head mismatch")
    return control


def _save_control(db,value):
    payload=dumps(value);queue=db.execute("SELECT agent,due_tick FROM cognition_queue ORDER BY agent").fetchall()
    db.execute("UPDATE runtime_state SET payload=?,checksum=? WHERE singleton=1",(payload,storage.digest(payload+dumps(queue))))


def atomic_json(path,value):
    path=Path(path);temporary=path.with_name(path.name+".tmp")
    with temporary.open("w",encoding="utf-8") as stream:
        stream.write(dumps(value)+"\n");stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)


def status(path):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute("BEGIN");_,_,_,_=storage._head(db);control=verify_control(db)
        control["queue_backlog"]=db.execute("SELECT COUNT(*) FROM cognition_queue").fetchone()[0]
        control["retained_epochs"]=db.execute("SELECT COUNT(*) FROM runtime_epochs").fetchone()[0]
    heartbeat=Path(str(path)+".heartbeat.json")
    if heartbeat.is_file():
        value=json.loads(heartbeat.read_text());value["age_s"]=max(0,time.time()-value["unix_time"]);control["heartbeat"]=value
    return control


def request_stop(path):
    heartbeat=Path(str(path)+".heartbeat.json")
    if not heartbeat.exists():raise ValueError("no supervised session heartbeat")
    value=json.loads(heartbeat.read_text())
    if value["status"]!="running":raise ValueError("supervised session is not running")
    atomic_json(str(path)+".stop.json",{"session":value["session"],"requested_at":time.time()})
    return {"stop_requested":True,"session":value["session"]}


def _prune_episodes(db,recent):
    protected=set()
    for (payload,) in db.execute("SELECT payload FROM plans"):
        plan=loads(payload)
        if plan.get("status")=="pending":protected.update(plan.get("evidence",[]))
    # Source records are irreplaceable. Their own references must resolve before
    # deletion, including older lessons and controller procedure evidence.
    kinds=('book_read','unverified_report','validated_practice','external_initialization',
           'operator_injection','knowledge_test_intent','knowledge_test','verified_procedure')
    for agent,ident,payload in db.execute('SELECT agent,id,payload FROM episodes WHERE kind IN ('+','.join('?' for _ in kinds)+')',kinds):
        protected.add(ident);record=loads(payload)
        lesson=record.get('lesson_episode_id')
        if lesson:
            if not db.execute('SELECT 1 FROM episodes WHERE id=? AND agent=?',(lesson,agent)).fetchone():
                raise ValueError('knowledge source reference unavailable before rotation')
            protected.add(lesson)
        requests=record.get('request_ids',[])+([record['request_id']] if 'request_id' in record else [])
        for rid in requests:
            row=db.execute('SELECT id FROM episodes WHERE agent=? AND source=?',(agent,'action:'+rid)).fetchone()
            if row:protected.add(row[0])
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_agents'").fetchone():
        from . import stabilization as stable
        stable.verify_event_chain(db)
        for (agent,) in db.execute('SELECT agent FROM stabilization_agents'):
            state=stable._load(db,agent);tasks=state.get('tasks',{})
            refs=[r['episode_id'] for r in tasks.get('procedures',{}).values()]
            for task in [tasks.get('active'),*tasks.get('history',[])]:
                if task:refs += [task[k] for k in ('procedure_source','procedure_episode_id','lesson_episode_id') if task.get(k)]
            for ident in refs:
                if not db.execute('SELECT 1 FROM episodes WHERE id=? AND agent=?',(ident,agent)).fetchone():
                    raise ValueError('controller source reference unavailable before rotation')
                protected.add(ident)
    removed=0
    for (agent,) in db.execute("SELECT agent FROM identities").fetchall():
        rows=db.execute("SELECT id FROM episodes WHERE agent=? AND kind NOT IN ('book_read','unverified_report','validated_practice') ORDER BY id DESC",(agent,)).fetchall()
        delete=[(r[0],) for r in rows[recent:] if r[0] not in protected]
        db.executemany("DELETE FROM episodes WHERE id=?",delete);removed+=len(delete)
    memory.seal(db);return removed


def _fingerprint(db):
    """Physical head alone cannot distinguish two different knowledge injections."""
    _,_,metadata,head=storage._head(db)
    values=[head,metadata,memory.checksum(db),verify_control(db)]
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone():
        values += [db.execute('SELECT * FROM stabilization_meta').fetchall(),
                   db.execute('SELECT * FROM stabilization_agents ORDER BY agent').fetchall(),
                   db.execute('SELECT checksum FROM stabilization_events ORDER BY id').fetchall()]
    return storage.digest(dumps(values))


def _controller_requests(db):
    """Preserve native journal rows until controller reconciliation, and its proofs."""
    keep=set()
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_agents'").fetchone():
        from . import stabilization as stable
        stable.verify_event_chain(db)
        for (agent,) in db.execute('SELECT agent FROM stabilization_agents'):
            state=stable._load(db,agent);pending=state['pending']
            if pending:
                row=db.execute("SELECT request FROM decisions WHERE json_extract(request,'$.request_id')=? AND json_extract(request,'$.agent_id')=?",(pending['request_id'],agent)).fetchone()
                if not row:raise ValueError('unsubmitted controller reservation; reconcile before rotation')
                if loads(row[0])!=pending:raise ValueError('controller reservation/journal mismatch')
                keep.add((agent,pending['request_id']))
            tasks=state.get('tasks',{})
            for task in [tasks.get('active'),*tasks.get('history',[])]:
                if task:
                    keep.update((agent,r['request_id']) for r in task.get('receipts',[]))
                    keep.update((agent,r) for r in task.get('evidence',[]))
                    keep.update((agent,r['request_id']) for r in task.get('native_failures',[]))
    for agent,payload in db.execute("SELECT agent,payload FROM episodes WHERE kind IN ('verified_procedure','knowledge_test','knowledge_test_intent')"):
        record=loads(payload)
        keep.update((agent,r) for r in record.get('request_ids',[]))
        if record.get('request_id'):keep.add((agent,record['request_id']))
    return keep


def _compact_controller(db,keep):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone():return 0
    from . import stabilization as stable
    rows=db.execute('SELECT id,checksum FROM stabilization_events ORDER BY id DESC').fetchall()
    deleted=rows[keep:]
    if not deleted:return 0
    payload,=db.execute('SELECT payload FROM stabilization_meta').fetchone();meta=loads(payload)
    meta['event_chain_anchor']=deleted[0][1]
    meta['archived_event_count']=meta.get('archived_event_count',0)+len(deleted)
    text=dumps(meta);db.execute('UPDATE stabilization_meta SET payload=?,checksum=?',(text,storage.digest(text)))
    db.execute('DELETE FROM stabilization_events WHERE id<=?',(deleted[0][0],))
    stable.verify_event_chain(db)
    return len(deleted)


def _archive_files(path):
    directory=Path(str(path)+".epochs")
    if directory.resolve().parent!=Path(path).resolve().parent:raise ValueError("archive directory escaped run folder")
    directory.mkdir(exist_ok=True)
    files=[]
    for file in directory.iterdir():
        if re.fullmatch(r"epoch-[0-9]{8}\.sqlite",file.name):files.append(file)
        elif ".tmp-" in file.name and re.fullmatch(r"epoch-[0-9]{8}\.sqlite\.tmp-[0-9a-f]{32}",file.name):
            # Only a previously interrupted backup's managed temporary file.
            if file.resolve().parent!=directory.resolve():raise ValueError("archive path escaped directory")
            file.unlink()
        else:raise ValueError("unmanaged file in checkpoint archive directory")
    return directory,sorted(files)


def verify_archives(path, limits=None):
    path=Path(path).resolve()
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');_,config,_,_=storage._head(db);control=verify_control(db)
        limits=limits or config.get('execution',DEFAULTS)
        records={r[0]:loads(r[1]) for r in db.execute('SELECT epoch,payload FROM runtime_epochs')}
    for epoch in range(max(1,control['epoch']-limits['checkpoint_keep']+1),control['epoch']+1):
        record=records.get(epoch)
        if not record:raise ValueError('retained archive record unavailable')
        file=Path(str(path)+'.epochs')/record['archive']
        if file.resolve().parent!=Path(str(path)+'.epochs').resolve() or not file.is_file():
            raise ValueError('retained archive missing or escaped directory')
        if hashlib.sha256(file.read_bytes()).hexdigest()!=record['archive_sha256']:
            raise ValueError('retained archive checksum mismatch')
    return {'epoch':control['epoch'],'verified_retained':min(control['epoch'],limits['checkpoint_keep'])}


def backup(path,name,output):
    """Explicit portable save: current DB plus its verified retained epoch files."""
    if output is None:raise ValueError('archive bundle requires an output path')
    path=Path(path).resolve();output=Path(output).resolve()
    with Lease(path):
        verified=verify_archives(path)
        directory=Path(str(output)+'.epochs')
        if directory.exists():raise FileExistsError('backup archive directory already exists')
        result=storage.save(path,name,output)
        directory.mkdir(exist_ok=False)
        with closing(storage._connect(path,readonly=True)) as db:
            control=verify_control(db)
            records=[loads(r[0]) for r in db.execute('SELECT payload FROM runtime_epochs ORDER BY epoch DESC LIMIT ?', (verified['verified_retained'],))]
        for record in records:
            source=Path(str(path)+'.epochs')/record['archive'];target=directory/record['archive']
            if source.resolve().parent!=Path(str(path)+'.epochs').resolve() or target.resolve().parent!=directory.resolve():
                raise ValueError('archive bundle path escaped directory')
            shutil.copy2(source,target)
        verify_archives(output)
        return result|{'archive_epoch':control['epoch'],'archive_files':len(records),'archive_directory':str(directory)}


def rotate(path,limits=None,fault=None):
    path=Path(path).resolve()
    with Lease(path):
        with closing(storage._connect(path,readonly=True)) as db:
            db.execute('BEGIN');world,config,metadata,before=storage._head(db);state=verify_control(db)
            fingerprint=_fingerprint(db);referenced=_controller_requests(db)
        limits=limits or config.get('execution',DEFAULTS)
        verify_archives(path,limits)
        number=state['epoch']+1;directory,files=_archive_files(path)
        output=directory/f'epoch-{number:08d}.sqlite'
        size=path.stat().st_size
        # Never delete the last valid recovery point to make a new backup fit.
        if sum(f.stat().st_size for f in files)+2*size>limits['max_archive_bytes']:
            raise ValueError('checkpoint archive disk quota reached')
        name=f'auto_epoch_{number}'
        if output.exists():
            with closing(storage._connect(output,readonly=True)) as archived:
                archived.execute('BEGIN')
                if _fingerprint(archived)!=fingerprint:raise ValueError('unfinished checkpoint does not match current physical/cognitive/controller head')
        else:
            with closing(storage._connect(path)) as recovery:
                recovery.execute('BEGIN IMMEDIATE')
                old=recovery.execute('SELECT state_hash FROM checkpoints WHERE name=?',(name,)).fetchone()
                if old:
                    if old[0]!=before:raise ValueError('unfinished checkpoint receipt does not match current head')
                    recovery.execute('DELETE FROM checkpoints WHERE name=?',(name,))
                recovery.commit()
            storage.save(path,name,output,_automated=True)
        storage.replay(output)
        if fault:fault('after_checkpoint',int(world.snapshot()['tick']))
        archive_hash=hashlib.sha256(output.read_bytes()).hexdigest()
        db=storage._connect(path)
        try:
            db.execute('BEGIN IMMEDIATE');world,_,metadata,current=storage._head(db)
            if _fingerprint(db)!=fingerprint:raise ValueError('head changed during checkpoint publication')
            control=verify_control(db);tick=int(world.snapshot()['tick'])
            removed=world._compact_history();events=world.step(0);world.check_invariants()
            episodes=_prune_episodes(db,limits['memory_recent'])
            controller_events=_compact_controller(db,max(16,limits['metrics_keep']))
            policy=metadata.pop('runtime_policy_state');native=world.checkpoint();hashed=storage.head_hash(native,policy)
            replay_after=db.execute('SELECT COALESCE(MAX(id),0) FROM decisions').fetchone()[0]
            metadata.update(replay_after_id=replay_after,retained_replay_start_tick=tick,epoch=number)
            for ident,request,source in db.execute('SELECT id,request,source FROM decisions').fetchall():
                r=loads(request)
                if source in ('operator','operator_knowledge') or (r.get('agent_id'),r.get('request_id')) in referenced:continue
                db.execute('DELETE FROM decisions WHERE id=?',(ident,))
            # Rebase the cursor to the retained maximum; a new SQLite row ID
            # must be greater than replay_after_id even after deleting a suffix.
            if replay_after and not db.execute('SELECT 1 FROM decisions WHERE id=?',(replay_after,)).fetchone():
                metadata['replay_after_id']=0 if not db.execute('SELECT 1 FROM decisions LIMIT 1').fetchone() else db.execute('SELECT MAX(id) FROM decisions').fetchone()[0]
            db.execute('DELETE FROM policy_frames')
            db.execute("DELETE FROM checkpoints WHERE name='initial' OR name GLOB 'auto_epoch_*'")
            db.execute("INSERT INTO checkpoints VALUES('initial',?,?,?,?,?)",(tick,native,hashed,storage.CHECKPOINT_SCHEMA,dumps(policy)))
            db.execute('UPDATE run SET metadata=?,state=?,state_hash=? WHERE singleton=1',(dumps(metadata),native,hashed))
            db.executemany('INSERT INTO events VALUES(?,?,?)',[(int(e['seq']),int(e['tick']),dumps(e)) for e in events])
            record={'epoch':number,'tick':tick,'before_hash':before,'after_hash':hashed,'archive':output.name,'archive_sha256':archive_hash,
                    'previous_chain':control.get('chain_head'),'requests_pruned':removed,'episodes_pruned':episodes,
                    'controller_events_pruned':controller_events,'event_counts':world.snapshot()['event_counts']}
            record['chain_hash']=storage.digest(dumps(record));db.execute('INSERT INTO runtime_epochs VALUES(?,?)',(number,dumps(record)))
            db.execute('DELETE FROM runtime_epochs WHERE epoch<=?',(number-limits['metrics_keep'],))
            control.update(epoch=number,last_rotation_tick=tick,chain_head=record['chain_hash']);_save_control(db,control)
            if fault:fault('rotation_before_commit',tick)
            db.commit()
            if fault:fault('rotation_after_commit',tick)
            db.execute('VACUUM')
        except BaseException:db.rollback();raise
        finally:db.close()
        # Only a verified, committed replacement permits eviction. All resolved
        # targets are checked in the intended archive directory before unlink.
        _,files=_archive_files(path)
        for old in files[:-limits['checkpoint_keep']]:
            if old.resolve().parent!=directory.resolve():raise ValueError('archive target escaped directory')
            old.unlink()
        return record


def dispatch(path,limits,provider=None):
    db=storage._connect(path)
    try:
        db.execute("BEGIN IMMEDIATE");world,config,_,_=storage._head(db);control=verify_control(db);tick=int(world.snapshot()["tick"])
        if config["cognition"]["provider"]=="disabled":db.commit();return []
        interval=config["cognition"]["interval_ticks"]
        if tick>=control.get("next_due_tick",0):
            for e in world.snapshot()["entities"]:
                if e["kind"]!="actor" or not e.get("alive",True) or not e.get("present",True):continue
                if db.execute("SELECT 1 FROM cognition_queue WHERE agent=?",(e["entity_id"],)).fetchone():continue
                if db.execute("SELECT COUNT(*) FROM cognition_queue").fetchone()[0]>=limits["queue_limit"]:control["queue_dropped"]+=1;continue
                db.execute("INSERT INTO cognition_queue VALUES(?,?)",(e["entity_id"],tick))
            control["next_due_tick"]=(tick//interval+1)*interval
        control["peak_queue_backlog"]=max(control.get("peak_queue_backlog",0),db.execute("SELECT COUNT(*) FROM cognition_queue").fetchone()[0]);_save_control(db,control);db.commit()
    except BaseException:db.rollback();raise
    finally:db.close()
    results=[]
    for _ in range(limits["calls_per_batch"]):
        with closing(storage._connect(path,readonly=True)) as db:
            storage._head(db)
            queued=db.execute("SELECT agent FROM cognition_queue ORDER BY due_tick,agent LIMIT 1").fetchone()
            if not queued:break
            # A crash after durable inference reservation/completion must not replay that inference.
            prior=db.execute("SELECT payload FROM cognition_calls WHERE agent=? AND tick=? ORDER BY id DESC LIMIT 1",(queued[0],tick)).fetchone()
        result={"status":"recovered_reserved_call"} if prior else storage.think(path,queued[0],provider)
        db=storage._connect(path)
        try:
            db.execute("BEGIN IMMEDIATE");control=verify_control(db)
            db.execute("DELETE FROM cognition_queue WHERE agent=?",queued);control["queue_served"]+=1
            key="dispatch_"+result["status"];control[key]=control.get(key,0)+1;_save_control(db,control);db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()
        results.append(result)
    return results


def metrics(path):
    snapshot=storage.inspect(path)
    with closing(storage._connect(path,readonly=True)) as db:
        control=verify_control(db);latencies=[];counts={};fallbacks=0;interrupted=0
        for (text,) in db.execute("SELECT payload FROM cognition_calls"):
            call=loads(text,65536);kind=call.get("status","unknown");counts[kind]=counts.get(kind,0)+1
            fallbacks+=kind=="fallback";interrupted+=kind in ("interrupted","interrupted_or_in_progress")
            if "latency_s" in call:latencies.append(call["latency_s"])
        def percentile(p):
            if not latencies:return None
            ordered=sorted(latencies);return ordered[math.ceil(p*len(ordered))-1]
        queue=db.execute("SELECT COUNT(*) FROM cognition_queue").fetchone()[0]
    archive=Path(str(path)+".epochs")
    return {"tick":snapshot["tick"],"simulated_time_s":snapshot["simulated_time_s"],"population":len([e for e in snapshot["entities"] if e["kind"]=="actor"]),
        "alive_present":sum(e["kind"]=="actor" and e.get("alive",True) and e.get("present",True) for e in snapshot["entities"]),
        "event_counts":snapshot["event_counts"],"invalid_actions":snapshot["event_counts"].get("action_rejected",0),
        "failed_actions":snapshot["event_counts"].get("action_failed",0),"cognition_statuses":counts,"fallbacks":fallbacks,"interrupted_calls":interrupted,
        "cognition_latency_p50_s":percentile(.5),"cognition_latency_p95_s":percentile(.95),"queue_backlog":queue,"runtime":control,
        "database_bytes":Path(path).stat().st_size,"archive_bytes":sum(p.stat().st_size for p in archive.glob("*.sqlite")) if archive.exists() else 0,
        "state_hash":snapshot["state_hash"],"build_id":snapshot["build_id"],"orchestration_id":storage.orchestration_id(),"memory":process_memory()}


def run(path,simulated_seconds,wall_seconds,provider=None,require_isolation=True,fault=None):
    from .isolation import token_status,network_probe
    path=Path(path).resolve()
    if not math.isfinite(simulated_seconds) or not 0<simulated_seconds<=86400 or not math.isfinite(wall_seconds) or not 0<wall_seconds<=3600:raise ValueError("bounded horizon must be <=86400 simulated s and <=3600 wall s")
    if require_isolation and not token_status()["appcontainer"]:raise ValueError("unattended closed execution requires the AppContainer launcher")
    started=time.perf_counter();deadline=started+wall_seconds;session=uuid.uuid4().hex;stop=threading.Event();heartbeat_done=threading.Event();lock=threading.Lock()
    heartbeat_errors=[]
    beat={"schema_version":1,"session":session,"pid":os.getpid(),"status":"running","tick":None,"started_utc":datetime.now(timezone.utc).isoformat(),"build_id":storage.load_native().build_id,"orchestration_id":storage.orchestration_id()}
    def heartbeat():
        while not heartbeat_done.is_set():
            with lock:copy=beat.copy()
            copy.update(unix_time=time.time(),wall_elapsed_s=time.perf_counter()-started)
            try:atomic_json(str(path)+".heartbeat.json",copy)
            except OSError as failure:heartbeat_errors.append(str(failure));stop.set();return
            heartbeat_done.wait(1)
    def stopping():
        file=Path(str(path)+".stop.json")
        if file.exists() and json.loads(file.read_text()).get("session")==session:stop.set()
        return stop.is_set() or time.perf_counter()>=deadline
    def committed(stage,tick):
        if stage=="after_commit":
            with lock:beat["tick"]=str(tick)
        if fault:fault(stage,tick)
    reason="system_failure";error=None;isolation=None
    with Lease(path):
        with closing(storage._connect(path,readonly=True)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone():
                raise ValueError('stabilized world requires living-world run; legacy supervisor cannot replace its scheduler')
        storage.recover(path);initial=storage.inspect(path);start_tick=int(initial["tick"]);dt=initial["dt_s"];target=start_tick+math.ceil(simulated_seconds/dt-1e-12)
        with closing(storage._connect(path,readonly=True)) as db:_,config,_,_=storage._head(db)
        limits=config.get("execution",DEFAULTS)
        beat["tick"]=initial["tick"]
        if require_isolation:
            isolation=network_probe()
            if not all(p["access_denied"] for p in isolation["connections"][:2]):raise ValueError("OS outbound-denial probes did not pass")
        thread=threading.Thread(target=heartbeat,name="supervision-heartbeat",daemon=True);thread.start()
        try:
            while True:
                current=storage.inspect(path);tick=int(current["tick"])
                if stopping():
                    if heartbeat_errors:raise OSError("heartbeat failed: "+heartbeat_errors[0])
                    reason="stopped" if stop.is_set() else "wall_limit";break
                if tick>=target:reason="target_reached";break
                if not any(e["kind"]=="actor" and e.get("alive",True) and e.get("present",True) for e in current["entities"]):reason="population_extinct";break
                with closing(storage._connect(path,readonly=True)) as db:control=verify_control(db)
                boundary=control["last_rotation_tick"]+limits["epoch_ticks"]
                if tick>=boundary:rotate(path,limits,fault);continue
                dispatch(path,limits,provider)
                storage._advance(path,min(limits["batch_ticks"],target-tick,boundary-tick),fault=committed,stop_requested=stopping)
        except (ValueError,sqlite3.Error,OSError,RuntimeError) as failure:
            error=f"{type(failure).__name__}: {failure}"
            reason="quota_reached" if "quota" in str(failure).lower() or "limit reached" in str(failure).lower() or "full" in str(failure).lower() else "system_failure"
        finally:
            with lock:beat.update(status=reason,error=error)
            heartbeat_done.set();thread.join(timeout=3)
            with lock:copy=beat.copy()
            copy.update(unix_time=time.time(),wall_elapsed_s=time.perf_counter()-started);atomic_json(str(path)+".heartbeat.json",copy)
        db=storage._connect(path);control_error=None
        try:
            db.execute("BEGIN IMMEDIATE");control=verify_control(db);control.update(status=reason,last_session=session,last_error=error);_save_control(db,control);db.commit()
        except sqlite3.Error as failure:
            db.rollback()
            if reason!="quota_reached":raise
            control_error=str(failure)
        finally:db.close()
        result=metrics(path);elapsed=time.perf_counter()-started
        result.update(status=reason,error=error,session=session,start_tick=str(start_tick),advanced_simulated_s=(int(result["tick"])-start_tick)*dt,
            requested_simulated_s=simulated_seconds,wall_time_s=elapsed,simulated_s_per_wall_s=(int(result["tick"])-start_tick)*dt/elapsed,isolation=isolation,final_control_error=control_error)
        atomic_json(str(path)+".report.json",result);return result
