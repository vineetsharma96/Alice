"""Exercise executable/source save interoperability with no external runtime on PATH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);directory=args.output.resolve();exe=(ROOT/'dist/UnderworldLab.exe').resolve()
    path=directory/'world with spaces.sqlite';backup=directory/'backup.sqlite'
    clean=os.environ.copy()
    for key in ('UNDERWORLD_BUILD','UNDERWORLD_TOOLCHAIN','PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):clean.pop(key,None)
    clean['PATH']=str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32')
    clean['UNDERWORLD_TOOLCHAIN']=str(directory/'absent-toolchain')
    source=os.environ|{'UNDERWORLD_BUILD':str(ROOT/'build/living-d'),'PYTHONPATH':str(ROOT)}
    report={'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'checks':[]}
    def run(command,env):
        start=time.perf_counter();result=subprocess.run(list(map(str,command)),cwd=directory,env=env,capture_output=True,text=True,timeout=90)
        row=dict(command=list(map(str,command)),returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,wall_s=time.perf_counter()-start);report['checks'].append(row)
        if result.returncode:raise RuntimeError(row)
        return result.stdout
    flags=['--db',path,'--seconds','.4','--port','0','--no-browser','--exit-after-run']
    for command,env,tick in (([exe,*flags],clean,'2'),([sys.executable,'-m','underworld.app',*flags],source,'4'),([exe,*flags],clean,'6')):
        rows=[json.loads(line) for line in run(command,env).splitlines()]
        assert rows[-1]['run']['tick']==tick and rows[-1]['run']['replay']['replay_matches']
    run([exe,'--cli','save','--db',path,'--name','package-smoke','--output',backup],clean)
    replay=json.loads(run([exe,'--cli','replay','--db',backup],clean));assert replay['replay_matches']
    a=json.loads(run([exe,'--cli','inspect','--db',path],clean));b=json.loads(run([exe,'--cli','inspect','--db',backup],clean))
    assert a['state_hash']==b['state_hash'] and a['tick']=='6'
    run([exe,'--cli','living-world','init','--db',directory/'cli-default.sqlite','--calls','0'],clean)
    report.update(passed=True,external_python_or_compiler_on_path=False,source_and_executable_resume_same_save=True,native_build_id=a['build_id'],backup_matches=True,tick=a['tick'])
    args.evidence.parent.mkdir(parents=True,exist_ok=True);args.evidence.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))


if __name__=='__main__':main()
