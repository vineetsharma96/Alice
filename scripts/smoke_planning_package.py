"""Exercise packaged E CLI, receipt-backed task, model-off guard and both UIs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);directory=args.output.resolve();path=directory/'E world.sqlite';exe=ROOT/'dist/UnderworldLab.exe'
    clean=os.environ.copy()
    for key in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','UNDERWORLD_BUILD','UNDERWORLD_TOOLCHAIN'):clean.pop(key,None)
    clean['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32');clean['UNDERWORLD_TOOLCHAIN']=str(directory/'missing-toolchain')
    report=dict(exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),checks=[])
    def run(args,expected=0):
        started=time.perf_counter();r=subprocess.run([str(exe),*map(str,args)],env=clean,cwd=directory,capture_output=True,text=True,timeout=90)
        report['checks'].append(dict(command=list(map(str,args)),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,wall_s=time.perf_counter()-started))
        if r.returncode!=expected:raise AssertionError(report['checks'][-1])
        return r.stdout,r.stderr
    run(['--db',path,'--seconds','.4','--port','0','--no-browser','--exit-after-run'])
    run(['--cli','living-world','task','--db',path,'--agent','agent-1','--goal','inspect_problem','--params','{"target":"resource-1"}'])
    run(['--db',path,'--seconds','3','--port','0','--no-browser','--exit-after-run'])
    state=json.loads(run(['--cli','living-world','status','--db',path])[0]);history=state['tasks']['history'][-1]
    assert history['goal']=='inspect_problem' and history['outcome']=='completed' and history['executor_goal_credit']
    run(['--cli','living-world','task','--db',path,'--agent','agent-1','--goal','craft_tool','--task-mode','model_assisted'])
    before=json.loads(run(['--cli','inspect','--db',path])[0])['state_hash']
    _,error=run(['--db',path,'--seconds','1','--port','0','--no-browser','--exit-after-run'],expected=2)
    assert 'model-off' in error
    assert before==json.loads(run(['--cli','inspect','--db',path])[0])['state_hash']
    run(['--cli','living-world','cancel-task','--db',path,'--agent','agent-1'])
    assert json.loads(run(['--cli','replay','--db',path])[0])['replay_matches']
    process=subprocess.Popen([str(exe),'--db',str(path),'--seconds','0','--port','0','--no-browser'],env=clean,cwd=directory,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        ready=json.loads(process.stdout.readline());report['viewer_url']=ready['url']
        output=ROOT/'artifacts/living_world_e_viewer'
        result=subprocess.run(['node','scripts/verify_ecology_viewer.mjs',ready['url'],str(output),'craft_tool'],cwd=ROOT,capture_output=True,text=True,timeout=90)
        report['browser']=dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
        assert result.returncode==0,report['browser']
    finally:
        subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],capture_output=True)
        process.wait(timeout=15)
    report.update(passed=True,external_runtime_on_path=False,completed_task=history,desktop_model_guard=True)
    args.evidence.parent.mkdir(parents=True,exist_ok=True);args.evidence.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','browser')},indent=2))


if __name__=='__main__':main()
