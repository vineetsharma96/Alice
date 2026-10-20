"""Host launcher and explicit local-inference broker for a network-disabled worker."""
import json
import math
from contextlib import closing
import multiprocessing
from pathlib import Path
import threading
import time
import uuid

from . import storage,cognition,runtime
from .isolation import AppContainer
from .wire import dumps


class PipeProvider:
    def __init__(self,connection):self.connection=connection
    def generate(self,context,budget):
        identifier=uuid.uuid4().hex;deadline=time.monotonic()+budget["timeout_s"]
        self.connection.send_bytes(dumps({"id":identifier,"context":context,"budget":budget}).encode())
        while time.monotonic()<deadline:
            if not self.connection.poll(max(0,deadline-time.monotonic())):break
            reply=json.loads(self.connection.recv_bytes(65536))
            if reply.get("id")!=identifier:continue
            if "error" in reply:raise ValueError(reply["error"])
            reply["details"]["transport"]="inherited IPC to explicit host loopback adapter"
            return reply["raw"],reply["details"]
        raise TimeoutError("local inference broker deadline")


def run_isolated(path,simulated_seconds,wall_seconds,local_model=False,endpoint="http://127.0.0.1:8081",fault_stage=None,fault_tick=None,broker_provider=None):
    if not math.isfinite(simulated_seconds) or not 0<simulated_seconds<=86400 or not math.isfinite(wall_seconds) or not 0<wall_seconds<=3600:raise ValueError("bounded horizon must be <=86400 simulated s and <=3600 wall s")
    path=Path(path).resolve();root=Path(__file__).resolve().parents[1]
    if not path.is_relative_to(root) or path.parent==root:raise ValueError("isolated runs require a dedicated output directory within this workspace")
    storage.recover(path)
    with closing(storage._connect(path,readonly=True)) as db:
        _,config,_,_=storage._head(db)
    if config["mode"]!="closed":raise ValueError("unattended launcher currently supports closed mode only")
    uses_model=config["cognition"]["provider"]=="llama.cpp"
    if uses_model!=local_model:raise ValueError("llama.cpp requires explicit --local-model; other providers must omit it")
    limits=config.get("execution",runtime.DEFAULTS)
    parent,child=multiprocessing.Pipe(duplex=True)
    provider=(broker_provider or cognition.LlamaCpp(endpoint)) if local_model else None
    send_lock=threading.Lock();busy=threading.Event();calls=0;broker_errors=[];started=time.monotonic()
    stdout=Path(str(path)+".worker.stdout.log");stderr=Path(str(path)+".worker.stderr.log")
    arguments=["-m","underworld.worker","--db",str(path),"--simulated-seconds",str(simulated_seconds),"--wall-seconds",str(wall_seconds)]
    if local_model:arguments.extend(["--broker-handle",str(child.fileno())])
    if fault_stage:arguments.extend(["--fault-stage",fault_stage,"--fault-tick",str(fault_tick)])
    def reply(value):
        try:
            with send_lock:parent.send_bytes(dumps(value).encode())
        except (OSError,EOFError):pass
    def infer(packet):
        try:
            raw,details=provider.generate(packet["context"],config["cognition"])
            reply({"id":packet["id"],"raw":raw,"details":details})
        except Exception as error:
            description=type(error).__name__+": "+str(error)[:240];broker_errors.append(description);reply({"id":packet["id"],"error":description})
        finally:busy.clear()
    with AppContainer(root,path.parent) as container:
        container.launch(arguments,stdout,stderr,handles=[child.fileno()] if local_model else [])
        child.close();stop_sent=None;watchdog=False;pipe_open=True
        try:
            while container.poll() is None:
                ready=False
                if local_model and pipe_open:
                    try:ready=parent.poll(.05)
                    except (EOFError,BrokenPipeError):pipe_open=False
                if ready:
                    try:packet=json.loads(parent.recv_bytes(16384))
                    except (EOFError,BrokenPipeError):pipe_open=False;continue
                    if type(packet) is not dict or set(packet)!={"id","context","budget"} or packet["budget"]!=config["cognition"] or type(packet["context"]) is not dict or set(packet["context"])!={"identity","perception","memories","relationships"}:
                        raise ValueError("invalid isolated inference packet")
                    calls+=1
                    if calls>limits["cognition_call_limit"] or busy.is_set():reply({"id":packet["id"],"error":"host broker quota or busy"})
                    else:busy.set();threading.Thread(target=infer,args=(packet,),daemon=True).start()
                else:time.sleep(.02)
                if time.monotonic()-started>wall_seconds+config["cognition"]["timeout_s"]+15:
                    container.kill();watchdog=True;break
        except KeyboardInterrupt:
            runtime.request_stop(path);stop_sent=time.monotonic()
            while container.poll() is None and time.monotonic()-stop_sent<config["cognition"]["timeout_s"]+5:time.sleep(.05)
            if container.poll() is None:container.kill();watchdog=True
        except BaseException:container.kill();raise
        for _ in range(100):
            if container.poll() is not None:break
            time.sleep(.02)
        exitcode=container.poll()
    parent.close()
    # Recover a hot rollback journal before reporting the authoritative committed head.
    storage.recover(path)
    if exitcode==0:
        result=json.loads(stdout.read_text(encoding="utf-8"))
    else:
        result={"status":"system_failure","error":f"isolated worker exited {exitcode}",**runtime.metrics(path)}
    result.update(worker_exitcode=exitcode,watchdog_terminated=watchdog,broker_calls=calls,broker_errors=broker_errors,
        host_wall_time_s=time.monotonic()-started,isolation_profile=json.loads((path.parent/"isolation-profile.json").read_text()))
    runtime.atomic_json(str(path)+".supervisor.json",result);return result
