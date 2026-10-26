"""Manual integrated-life controls; paused initially, no overall tick horizon."""
import argparse
from collections import deque
from contextlib import closing
import json
import math
from pathlib import Path
import secrets
import threading
import time
import webbrowser

from . import life_store as store, life_viewer, time_dilation, weather_store as weather
from .lease import Lease


class Control:
    def __init__(self,path):
        self.path=Path(path).resolve();initial=store.inspect(self.path)
        self.token=secrets.token_urlsafe(32);self.lock=threading.Lock()
        self.closed=threading.Event();self.ready=threading.Event()
        self.paused=True;self.pending=deque();self.error=None;self.speed=1
        self.dilation='normal'
        self.job=None;self.last_job=None;self.cancel_requested=False
        self.tick=initial['snapshot']['tick'];self.seconds=initial['snapshot']['simulated_time_s'];self.dt=float(initial['snapshot'].get('dt_s',.25))
        self.thread=threading.Thread(target=self._run,name='alice-manual-writer',daemon=False)

    def status(self):
        with self.lock:
            return dict(paused=self.paused,error=self.error,tick=self.tick,
                simulated_s=self.seconds,speed=self.speed,queued=len(self.pending),
                processing=bool(self.job),job=dict(self.job) if self.job else None,
                last_job=dict(self.last_job) if self.last_job else None,
                time_dilation=time_dilation.public(self.dilation),
                overall_tick_limit=None)

    def command(self,payload):
        if type(payload) is not dict or 'command' not in payload:raise ValueError('Expected a control command')
        command=payload['command']
        with self.lock:
            if command=='pause':
                self.paused=True
                if self.job:self.job['state']='paused'
            elif command=='resume':
                if self.error:raise ValueError(self.error)
                if self.job:
                    self.job['state']='processing';self.cancel_requested=False;self.paused=False
                else:self.paused=False
            elif command=='speed':
                value=payload.get('value')
                if set(payload)!={'command','value'} or isinstance(value,bool) or type(value) not in (int,float) or not math.isfinite(float(value)) or value not in (1,5,20):
                    raise ValueError('speed must be 1, 5 or 20')
                self.speed=float(value)
            elif command=='time_dilation':
                if set(payload)!={'command','preset'} or not isinstance(payload.get('preset'),str):
                    raise ValueError('time_dilation requires a preset')
                self.dilation=time_dilation.get(payload['preset']).id
            elif command in ('tick','turn'):
                if self.error:raise ValueError(self.error)
                if not self.paused or self.job:raise ValueError('Pause before stepping')
                if len(self.pending)>=8:raise ValueError('Step queue full')
                self.pending.append(command)
            elif command in ('step_batch','run_until'):
                if self.error:raise ValueError(self.error)
                if not self.paused:raise ValueError('Pause before stepping')
                if self.job or self.pending:raise ValueError('A stepping job is already active')
                if command=='step_batch':
                    ticks=payload.get('ticks')
                    if type(ticks) is not int or not 1<=ticks<=100000:raise ValueError('ticks must be an integer in [1,100000]')
                    self.job=dict(kind='step_batch',total=ticks,completed=0,remaining=ticks,state='processing',started_tick=self.tick,target_s=None)
                else:
                    target=payload.get('simulated_s')
                    if type(target) not in (int,float) or not math.isfinite(float(target)) or float(target)<=self.seconds:
                        raise ValueError('run_until requires a future simulated time')
                    target=float(target);ticks=(target-self.seconds)/self.dt
                    if not math.isclose(ticks,round(ticks),rel_tol=0.0,abs_tol=1e-9):
                        raise ValueError(f'run_until target must align to the native timestep ({self.dt:g} simulated seconds)')
                    self.job=dict(kind='run_until',total=None,completed=0,remaining=None,state='processing',started_tick=self.tick,target_s=float(target))
                self.paused=False
                self.cancel_requested=False
            elif command=='cancel_step':
                if not self.job:raise ValueError('No stepping job is active')
                self.cancel_requested=True
            elif command=='force_weather':
                if self.error:raise ValueError(self.error)
                if not self.paused or self.job:raise ValueError('Pause before applying weather')
                parameters=payload.get('parameters')
                if type(parameters) is not dict:raise ValueError('Weather parameters are required')
                ident=parameters.get('id')
                if type(ident) is not str or not ident:raise ValueError('Weather override needs an id')
                if len(self.pending)>=8:raise ValueError('Control queue full')
                self.pending.append({'kind':'force_weather','parameters':dict(parameters),'logical_id':f'weather-{ident}'})
            else:raise ValueError('Unknown manual control')
        return self.status()

    def start(self):
        self.thread.start()
        if not self.ready.wait(10):raise RuntimeError('Writer did not become ready')
        if self.error:raise ValueError(self.error)

    def _run(self):
        try:
            with Lease(self.path):
                self.ready.set()
                while not self.closed.wait(.001 if time_dilation.get(self.dilation).scale > 1 else .03):
                    with self.lock:
                        job=dict(self.job) if self.job else None
                        if job and self.cancel_requested:
                            self.last_job=dict(job,state='cancelled',finished_tick=self.tick,finished_s=self.seconds)
                            self.job=None;self.cancel_requested=False;self.paused=True;mode=None
                        elif job and self.paused:
                            self.job['state']='paused';mode=None
                        elif job:
                            self.job['state']='processing';mode='job'
                        else:mode=self.pending.popleft() if self.pending else ('turn' if not self.paused else None)
                    if mode is None:continue
                    before=store.inspect(self.path);started=time.monotonic()
                    if isinstance(mode,dict) and mode.get('kind')=='force_weather':
                        store.commit(self.path,dict(kind='force',parameters=mode['parameters']),mode['logical_id'])
                        after=store.inspect(self.path)['snapshot']
                        with self.lock:
                            self.tick=after['tick'];self.seconds=after['simulated_time_s']
                        continue
                    if mode=='job':command=dict(kind='step',ticks=1)
                    else:
                        agent,_=store.next_turn(self.path)
                        if agent is None:raise ValueError('No living inhabitant remains')
                        command=dict(kind='step',ticks=1) if mode=='tick' else dict(kind='emotion-policy',agent=agent)
                    store.commit(self.path,command,f"manual-{before['operations']}")
                    after=store.inspect(self.path)['snapshot']
                    with self.lock:
                        self.tick=after['tick'];self.seconds=after['simulated_time_s']
                        if self.job:
                            self.job['completed']+=1
                            if self.job['kind']=='step_batch':self.job['remaining']=max(0,self.job['total']-self.job['completed'])
                            else:self.job['remaining_s']=max(0.0,self.job['target_s']-self.seconds)
                            done=self.cancel_requested or (self.job['kind']=='step_batch' and self.job['remaining']==0) or (self.job['kind']=='run_until' and self.seconds+1e-9>=self.job['target_s'])
                            if done:
                                outcome='cancelled' if self.cancel_requested else 'completed'
                                self.last_job=dict(self.job,state=outcome,finished_tick=self.tick,finished_s=self.seconds)
                                self.job=None;self.cancel_requested=False;self.paused=True
                            pause=self.paused and not self.job
                        else:pause=self.paused
                    # Pace continuous play in simulated seconds; every native
                    # action and cognitive update still commits normally.
                    if not pause:self.closed.wait(max(0,(self.seconds-before['snapshot']['simulated_time_s'])/
                        max(.01,self.speed*time_dilation.get(self.dilation).scale)-(time.monotonic()-started)))
        except Exception as error:
            with self.lock:
                self.error=str(error);self.paused=True;self.pending.clear()
                if self.job:
                    self.last_job=dict(self.job,state='failed',error=str(error),finished_tick=self.tick,finished_s=self.seconds)
                    self.job=None;self.cancel_requested=False
        finally:self.ready.set()

    def close(self):
        self.closed.set()
        if self.thread.ident:self.thread.join()


SCRIPT=b"""const box=document.createElement('section');
box.innerHTML='<h2>Manual controls</h2><button id="life-play">Run / Resume</button> <button id="life-pause">Pause</button> <button id="life-tick">Step 1 tick</button> <button id="life-turn">One inhabitant turn</button><p id="life-control-status" role="status">Paused</p><p>No overall tick limit. Native resource and journal limits remain active.</p>';
document.querySelector('aside').prepend(box);
let token;
async function status(){try{const r=await fetch('/api/life-control');const s=await r.json();if(!r.ok)throw Error(s.error);token=s.token;document.getElementById('life-control-status').textContent=s.error?s.error:`${s.paused?'Paused':'Running'} - tick ${s.tick} - ${s.simulated_s.toFixed(2)} simulated seconds - ${s.queued} queued`;for(const id of ['life-tick','life-turn'])document.getElementById(id).disabled=!s.paused||!!s.error;}catch(e){document.getElementById('life-control-status').textContent=e.message;}}
for(const [id,command] of [['life-play','resume'],['life-pause','pause'],['life-tick','tick'],['life-turn','turn']])document.getElementById(id).onclick=async()=>{try{const r=await fetch('/api/life-control',{method:'POST',headers:{'Content-Type':'application/json','X-Life-Control':token},body:JSON.stringify({command})});const s=await r.json();if(!r.ok)throw Error(s.error);await status();}catch(e){document.getElementById('life-control-status').textContent=e.message;}};
status();setInterval(status,1000);
"""


def server(path,port=8782):
    control=Control(path);http=life_viewer.server(path,port);base=http.RequestHandlerClass
    class Handler(base):
        def authorized_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def send(self,status,body,mime='application/json'):
            return super().send(status,body,mime)
        def do_GET(self):
            if not self.authorized_host():self.send(403,b'{"error":"Invalid host"}');return
            if self.path=='/api/life-control':
                self.send(200,json.dumps(dict(control.status(),token=control.token)).encode());return
            if self.path=='/life-controls.js':self.send(200,SCRIPT,'text/javascript');return
            super().do_GET()
        def do_POST(self):
            if not self.authorized_host() or self.headers.get('X-Life-Control')!=control.token:
                self.send(403,b'{"error":"Unauthorized control"}');return
            if self.path!='/api/life-control':self.send(404,b'{"error":"Not found"}');return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 1<=size<=4096 or self.headers.get('Content-Type')!='application/json':raise ValueError('Invalid control payload')
                self.send(200,json.dumps(control.command(json.loads(self.rfile.read(size)))).encode())
            except (ValueError,UnicodeError) as error:self.send(400,json.dumps(dict(error=str(error))).encode())
    http.RequestHandlerClass=Handler
    return http,control


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--source',type=Path)
    p.add_argument('--port',type=int,default=8782);p.add_argument('--no-browser',action='store_true');a=p.parse_args()
    if not a.db.exists():
        if a.source is None:p.error('Use --source to create a new control-session copy')
        weather.save(a.source,a.db)
    http,control=server(a.db,a.port)
    try:
        control.start();print(json.dumps(dict(url=f'http://127.0.0.1:{http.server_port}/',db=str(a.db.resolve()),**control.status())),flush=True)
        if not a.no_browser:webbrowser.open(f'http://127.0.0.1:{http.server_port}/')
        http.serve_forever(poll_interval=.1)
    except KeyboardInterrupt:pass
    finally:control.close();http.server_close()


if __name__=='__main__':main()
