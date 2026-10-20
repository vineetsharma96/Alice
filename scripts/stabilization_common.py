"""Owned pinned local server and native-only fixture helpers; no downloads."""
from contextlib import contextmanager, closing
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage
from underworld.config import load


@contextmanager
def model_server(folder,port=8082):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1',port))==0: raise ValueError('refusing existing model listener')
    folder.mkdir(parents=True,exist_ok=True)
    with (folder/'model.stdout.log').open('wb') as out,(folder/'model.stderr.log').open('wb') as err:
        server=subprocess.Popen([str(ROOT/'.tools/llama-b11721/llama-server.exe'),'-m',str(ROOT/'models/smollm2-360m-instruct-q8_0.gguf'),
            '--host','127.0.0.1','--port',str(port),'-c','2048','-t','2','-tb','2','--parallel','1','-ngl','0','--no-ui'],
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        try:
            deadline=time.monotonic()+45
            while True:
                try:
                    with urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as r:
                        if r.status==200:break
                except OSError: pass
                if server.poll() is not None or time.monotonic()>deadline: raise RuntimeError('model startup failed')
                time.sleep(.2)
            yield f'http://127.0.0.1:{port}'
        finally:
            if server.poll() is None:server.terminate()
            server.wait(timeout=10)


def create(path,seed=101,food=.8,water=1.2,population=2,utility=False,age=0):
    cfg=load(ROOT/'config/survival.toml');cfg['seed']=seed
    cfg['world'].update(population=population,population_limit=population,dt_s=1.)
    cfg['agency'].update(policy='utility' if utility else 'none',interval_ticks=1,food_kg=food,water_kg=water)
    cfg['cognition'].update(max_input_tokens=1536,max_output_tokens=128,timeout_s=20)
    storage.create(path,cfg,scripted=False)
    if age:storage.advance(path,age)
    return path


def clone(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb'):pass
    import sqlite3
    with closing(sqlite3.connect(source)) as src,closing(sqlite3.connect(target)) as dst:src.backup(dst)


def read(path,table):
    with closing(storage._connect(path,readonly=True)) as db:
        return [dict(zip([c[0] for c in cursor.description],r)) for cursor in [db.execute('SELECT * FROM '+table)] for r in cursor.fetchall()]


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
