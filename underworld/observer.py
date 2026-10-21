"""Loopback-only observer. GET is read-only; explicit token-bearing POST controls the writer."""
import json
import math
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import storage
from . import teaching
from .wire import loads


def controller_projection(db,selected):
    attached=db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone()
    if not attached:return {'active':'legacy','stabilization':None}
    from .stabilization import _load
    from .stabilization import verify_event_chain
    verify_event_chain(db)
    managed=db.execute('SELECT 1 FROM stabilization_agents WHERE agent=?',(selected,)).fetchone()
    return {'active':'stabilization','selected_managed':bool(managed),
            'stabilization':_load(db,selected) if managed else None}


class Controller:
    def __init__(self,path,readonly=False):
        if not readonly:
            db=storage._connect(path,readonly=True)
            try:
                stabilized=db.execute("SELECT 1 FROM sqlite_master WHERE name='stabilization_meta'").fetchone()
            finally:db.close()
            if stabilized:raise ValueError('stabilized world requires --read-only; use living-world run for its scheduler')
        if readonly:storage.inspect(path)
        else:storage.recover(path)
        self.readonly=readonly
        self.advance_wall=0.0
        self.advanced_simulated=0.0
        self.path=Path(path)
        self.lock=threading.RLock()
        self.paused=True
        self.speed=1.0
        self.error=None
        self.closed=threading.Event()
        self.token=secrets.token_urlsafe(32)
        self.operator_token=secrets.token_urlsafe(32)
        self.dt=storage.inspect(path)["dt_s"]
        self.worker=None

    def start(self):
        if self.readonly:return
        self.worker=threading.Thread(target=self._run,name="underworld-writer",daemon=True)
        self.worker.start()

    def state(self,agent=None):
        # Both UIs read one SQLite snapshot, even while the CLI advances the world.
        from .viewer import packet
        result=packet(self,agent)
        state={key:result[key] for key in ("snapshot","selected","mind","controller","procedure","knowledge","integration","controls")}
        snapshot=result['snapshot']
        state['operator_history']={key:snapshot.get(key) for key in ('branch_id','laws_version','parent_branch_id')}
        state['operator_history']['interventions']=list(reversed(result['operator_history']))
        return state

    def control(self,payload):
        if type(payload) is not dict or "command" not in payload:raise ValueError("invalid command")
        with self.lock:
            if self.readonly:raise ValueError('read-only attachment; control the isolated runner separately')
            command=payload["command"]
            if command in ("pause","resume","step") and set(payload)!={"command"}:raise ValueError("extra fields")
            if command=="pause":self.paused=True
            elif command=="resume":
                if self.error:raise ValueError("writer failed; restart observer after resolving the reported error")
                self.paused=False
            elif command=="step":
                if not self.paused:raise ValueError("pause before stepping")
                start=time.perf_counter();storage.advance(self.path,1)
                self.advance_wall+=time.perf_counter()-start;self.advanced_simulated+=self.dt
            elif command=="speed":
                if set(payload)!={"command","value"} or type(payload["value"]) not in (int,float):raise ValueError("invalid speed")
                value=payload["value"]
                if not math.isfinite(value) or value not in (1,5,20):raise ValueError("speed must be 1, 5 or 20")
                self.speed=float(value)
            else:raise ValueError("unknown command")
            return {"paused":self.paused,"speed":self.speed}

    def intervene(self,payload):
        with self.lock:
            if self.readonly:raise ValueError('read-only attachment')
            if not self.paused:raise ValueError("pause before an operator intervention")
            return teaching.intervene(self.path,payload)

    def _run(self):
        while not self.closed.wait(.02):
            with self.lock:
                if self.paused:continue
                # Bound writer batches for responsive controls; speed is a target, never skipped ticks.
                ticks=max(1,min(5,round(.1*self.speed/self.dt)))
                start=time.perf_counter()
                try:
                    storage.advance(self.path,ticks)
                    self.advance_wall+=time.perf_counter()-start;self.advanced_simulated+=ticks*self.dt
                except Exception as error:
                    self.error=str(error);self.paused=True
                    continue
                delay=max(0,ticks*self.dt/self.speed-(time.perf_counter()-start))
            self.closed.wait(delay)

    def close(self):
        self.closed.set()
        if self.worker:self.worker.join(timeout=30)


def make_server(path,port=8765,readonly=False):
    controller=Controller(path,readonly)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass

        def reply(self,value,status=200,content_type="application/json"):
            body=value.encode("utf-8") if isinstance(value,str) else json.dumps(value,allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",content_type+"; charset=utf-8")
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            try:
                self.end_headers()
                self.wfile.write(body)
            except ConnectionError:
                # A tab can leave during polling; there is no client to receive an error response.
                self.close_connection=True

        def valid_host(self):
            return self.headers.get("Host")==f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():return self.reply({"error":"invalid host"},403)
            url=urlsplit(self.path)
            try:
                if url.path=="/api/state":
                    agent=parse_qs(url.query).get("agent",[None])[0]
                    return self.reply(controller.state(agent))
                if url.path=="/api/session":return self.reply({"token":controller.token,"operator_token":controller.operator_token})
                if url.path=="/api/viewer":
                    from .viewer import packet
                    query=parse_qs(url.query)
                    return self.reply(packet(controller,query.get('agent',[None])[0],query.get('after',['0'])[0]))
                if url.path=="/api/interventions":return self.reply(teaching.history(controller.path))
                if url.path=="/favicon.ico":return self.reply("",204,"image/x-icon")
                files={"/":("observer.html","text/html"),"/observer.js":("observer.js","text/javascript"),
                       "/observer.css":("observer.css","text/css"),'/viewer':('viewer.html','text/html'),
                       '/viewer.js':('viewer.js','text/javascript'),'/scene.js':('scene.js','text/javascript'),'/viewer.css':('viewer.css','text/css'),
                       **{'/vendor/'+name:('vendor/'+name,'text/javascript' if name.endswith('.js') else 'text/plain') for name in ('three.module.min.js','three.core.min.js','OrbitControls.js','LICENSE.three','manifest.json')}}
                if url.path not in files:return self.reply({"error":"not found"},404)
                name,kind=files[url.path]
                self.reply((Path(__file__).parent/"web"/name).read_text(encoding="utf-8"),content_type=kind)
            except (ValueError,OSError,RuntimeError,sqlite3.Error) as error:self.reply({"error":str(error)},400)

        def do_POST(self):
            expected=f"http://127.0.0.1:{self.server.server_port}"
            intervention=self.path=="/api/interventions"
            valid_token=(self.headers.get("X-Operator-Token")==controller.operator_token if intervention else self.headers.get("X-Observer-Token")==controller.token)
            if not self.valid_host() or self.headers.get("Origin",expected)!=expected or not valid_token:
                return self.reply({"error":"unauthorized observer control"},403)
            if self.path not in ("/api/control","/api/interventions"):return self.reply({"error":"not found"},404)
            try:
                size=int(self.headers.get("Content-Length","0"))
                limit=16384 if intervention else 1024
                if not 1<=size<=limit or self.headers.get("Content-Type")!="application/json":raise ValueError("invalid control payload")
                payload=loads(self.rfile.read(size).decode("utf-8"),limit)
                self.reply(controller.intervene(payload) if intervention else controller.control(payload))
            except (ValueError,OSError,RuntimeError,sqlite3.Error) as error:self.reply({"error":str(error)},400)
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    server.daemon_threads=True
    return server,controller


def serve(path,port=8765,readonly=False):
    server,controller=make_server(path,port,readonly)
    controller.start()
    print(f"3D viewer: http://127.0.0.1:{server.server_port}/viewer (read-only={readonly}; paused; Ctrl+C to stop)",flush=True)
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:
        controller.close()
        server.server_close()
