"""Current-runtime checks after review; run serially after the test suite."""
import copy
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import runtime,storage
from underworld.config import load
from underworld.resources import process_memory
from underworld.supervisor import run_isolated


def main():
    folder=ROOT/'data/phase7-reviewed';folder.mkdir(exist_ok=False)
    report={'orchestration_id':storage.orchestration_id(),'native_build_id':storage.load_native().build_id,'cases':[],
        'method':'serial checks after full tests; seed 11, 120 simulated seconds, 60 wall-second cap, dt 1, epoch 50, batch 25'}
    artifact=ROOT/'artifacts/phase7_final_validation.json';base=load(ROOT/'config/unattended.toml')
    def case(name,population=8,model=False):
        path=folder/name/'run.sqlite';config=copy.deepcopy(base);config['seed']=11
        config['world'].update(population=population,population_limit=population)
        config['execution'].update(epoch_ticks=50,batch_ticks=25,cognition_call_limit=2)
        if model:config['cognition'].update(provider='llama.cpp',max_input_tokens=1536,max_output_tokens=128,timeout_s=20)
        storage.create(path,config);initial=path.stat().st_size
        result=run_isolated(path,120,60,local_model=model)
        result.update(case=name,path=str(path),configuration=config,initial_database_bytes=initial,database_growth_bytes=path.stat().st_size-initial,replay=storage.replay(path))
        report['cases'].append(result);runtime.atomic_json(artifact,report)
        print(name,result['status'],result['tick'],round(result['simulated_s_per_wall_s'],2),flush=True)
        return result
    for population in (8,16,32):case(f'population-{population}',population)
    import socket
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8081))==0:raise ValueError('refusing existing model listener')
    binary=ROOT/'.tools/llama-b11721/llama-server.exe';model=ROOT/'models/smollm2-360m-instruct-q8_0.gguf'
    with (folder/'model.stdout.log').open('wb') as out,(folder/'model.stderr.log').open('wb') as err:
        server=subprocess.Popen([str(binary),'-m',str(model),'--host','127.0.0.1','--port','8081','-c','2048','-t','2','-tb','2','--parallel','1','-ngl','0','--no-ui'],cwd=ROOT,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
        report['model_server']={'pid':server.pid,'stopped':False}
        try:
            deadline=time.monotonic()+45
            while True:
                try:
                    with urlopen('http://127.0.0.1:8081/health',timeout=1) as response:
                        if response.status==200:break
                except OSError:pass
                if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('server startup failed')
                time.sleep(.2)
            case('local-model',model=True)['model_server_memory']=process_memory(server.pid)
        finally:
            server.terminate();server.wait(timeout=10);report['model_server'].update(stopped=True,exitcode=server.returncode);runtime.atomic_json(artifact,report)
    if not all(c['status'] in ('target_reached','wall_limit') and c['isolation_profile']['cleaned'] and c['replay']['replay_matches'] for c in report['cases']):raise AssertionError('reviewed validation failed')


if __name__=='__main__':main()
