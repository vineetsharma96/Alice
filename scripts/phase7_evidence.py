"""Short, bounded Phase 7 evidence. Long horizons and 3D are deliberately deferred."""
import argparse
from contextlib import closing
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import runtime,storage
from underworld.config import load
from underworld.resources import process_memory
from underworld.supervisor import run_isolated

SEEDS=[11,22,33,44,55]
BASE=load(ROOT/'config/unattended.toml')
OUTPUT=ROOT/'data/phase7-final'
ARTIFACT=ROOT/'artifacts/phase7_summary.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',action='store_true');args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=False)
    report={'phase':7,'seed_set':SEEDS,'native_build':storage.load_native().build_id,'orchestration_id':storage.orchestration_id(),
        'scope':'short operational validation; 24-hour and longer multi-seed horizons and 3D deferred by user',
        'dt_s':1,'all_agents_updated_every_tick':True,'cases':[],'recovery':[],'diagnostics':[]}
    started=time.monotonic()
    def publish():
        report['elapsed_host_wall_s']=time.monotonic()-started;runtime.atomic_json(ARTIFACT,report)
    def case(name,seed=11,population=8,provider='disabled',seconds=300,memory=True,wall=35,**overrides):
        path=OUTPUT/name/'run.sqlite';config=copy.deepcopy(BASE);config['seed']=seed
        config['world'].update(population=population,population_limit=population)
        config['cognition'].update(provider=provider,max_input_tokens=1536,max_output_tokens=128,timeout_s=20)
        config['execution'].update(batch_ticks=25,epoch_ticks=100,cognition_call_limit=4 if provider=='baseline' else 2,episodic_memory=memory)
        for section,values in overrides.items():config[section].update(values)
        storage.create(path,config);initial_bytes=path.stat().st_size
        runtime.atomic_json(path.parent/'config.json',config)
        result=run_isolated(path,seconds,wall,local_model=provider=='llama.cpp')
        result.update(case=name,seed=seed,arm='no_episodes' if not memory else provider,path=str(path),initial_database_bytes=initial_bytes,
            database_growth_bytes=result['database_bytes']-initial_bytes,replay=storage.replay(path),configuration=config)
        print(f"{name}: {result['status']} tick={result['tick']} speed={result.get('simulated_s_per_wall_s',0):.2f} fallback={result['fallbacks']}",flush=True)
        return result
    for population in (8,16,32):
        report['cases'].append(case(f'population-{population}',population=population,wall=60));publish()
    for seed in SEEDS:
        if seed!=11:report['cases'].append(case(f'utility-{seed}',seed=seed));publish()
        report['cases'].append(case(f'baseline-{seed}',seed=seed,provider='baseline'));publish()
        report['cases'].append(case(f'no-episodes-{seed}',seed=seed,memory=False));publish()
    if args.model:
        binary=ROOT/'.tools/llama-b11721/llama-server.exe';weight=ROOT/'models/smollm2-360m-instruct-q8_0.gguf'
        if hashlib.sha256(weight.read_bytes()).hexdigest()!='48ab3034d0dd401fbc721eb1df3217902fee7dab9078992d66431f09b7750201':raise ValueError('model pin mismatch')
        # Refuse to adopt an unrelated listener. This script owns and later stops its server.
        import socket
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1',8081))==0:raise ValueError('8081 already owned; no model server started')
        with (OUTPUT/'model.stdout.log').open('wb') as out,(OUTPUT/'model.stderr.log').open('wb') as err:
            server=subprocess.Popen([str(binary),'-m',str(weight),'--host','127.0.0.1','--port','8081','-c','2048','-t','2','-tb','2','--parallel','1','-ngl','0','--no-ui'],cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
            report['model_server']={'pid':server.pid,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(weight.read_bytes()).hexdigest(),'stopped':False}
            try:
                deadline=time.monotonic()+45
                while True:
                    try:
                        with urlopen('http://127.0.0.1:8081/health',timeout=1) as response:
                            if response.status==200:break
                    except OSError:pass
                    if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('pinned server startup failed')
                    time.sleep(.2)
                for seed in SEEDS:
                    result=case(f'model-{seed}',seed=seed,provider='llama.cpp',seconds=120,wall=60,
                        execution={'batch_ticks':10})
                    result['model_server_memory']=process_memory(server.pid);report['cases'].append(result);publish()
            finally:
                server.terminate();server.wait(timeout=10);report['model_server'].update(stopped=True,exitcode=server.returncode);publish()
    for stage,expected in [('before_commit',2),('after_commit',3),('after_checkpoint',10)]:
        path=OUTPUT/f'crash-{stage}'/'run.sqlite';config=copy.deepcopy(BASE);config['world'].update(population=2,population_limit=2)
        config['execution'].update(batch_ticks=5,epoch_ticks=10);storage.create(path,config)
        trigger=10 if stage=='after_checkpoint' else 3
        failed=run_isolated(path,30,20,fault_stage=stage,fault_tick=trigger)
        if failed['status']!='system_failure' or int(failed['tick'])!=expected:raise AssertionError('wrong forced-exit recovery boundary')
        resumed=run_isolated(path,3,20)
        if int(resumed['tick'])!=expected+3:raise AssertionError('resume skipped or lost committed tick')
        report['recovery'].append({'stage':stage,'committed_tick':expected,'failed':failed,'resumed':resumed,'replay':storage.replay(path)});publish()
    report['diagnostics'].append(case('disk-quota',population=32,seconds=300,wall=60,execution={'max_db_bytes':1048576,'epoch_ticks':10000}))
    report['diagnostics'].append(case('extinction',population=2,seconds=1500,wall=40,agency={'policy':'none','food_kg':0,'water_kg':0,'food_regen_kg_s':0,'water_regen_kg_s':0}));publish()
    path=OUTPUT/'graceful-stop'/'run.sqlite';storage.create(path,BASE);errors=[]
    def stopper():
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            file=Path(str(path)+'.heartbeat.json')
            if file.exists():
                beat=json.loads(file.read_text())
                if beat['status']=='running' and int(beat['tick'] or 0)>0:
                    try:runtime.request_stop(path)
                    except Exception as failure:errors.append(str(failure))
                    return
            time.sleep(.05)
        errors.append('stop request was not delivered')
    thread=threading.Thread(target=stopper,daemon=True);thread.start()
    stopped=run_isolated(path,1000,40);thread.join(timeout=1)
    report['diagnostics'].append(stopped|{'case':'graceful-stop','stop_errors':errors,'replay':storage.replay(path)});publish()
    rows=[]
    for result in report['cases']:
        rows.append({key:result.get(key) for key in ('case','seed','arm','population','status','advanced_simulated_s','wall_time_s','host_wall_time_s','simulated_s_per_wall_s','cognition_latency_p50_s','cognition_latency_p95_s','fallbacks','queue_backlog','invalid_actions','database_bytes','archive_bytes','database_growth_bytes')})
    with (ROOT/'artifacts/phase7_summary.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    print(f"Evidence: {ARTIFACT}; host wall={time.monotonic()-started:.1f}s",flush=True)


if __name__=='__main__':main()
