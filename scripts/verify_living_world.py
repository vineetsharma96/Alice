"""Retain current living-world regression evidence without replacing old studies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=ROOT/'build/living-d')
    p.add_argument('--ctest',default='ctest')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=420)
    args=p.parse_args();build=args.build.resolve()
    core_name='underworld_core.exe' if os.name=='nt' else 'underworld_core'
    core=build/core_name
    if not core.exists() and (build/'Release'/core_name).exists():core=build/'Release'/core_name
    env=os.environ|{'UNDERWORLD_BUILD':str(build),'UNDERWORLD_CORE':str(core)}
    os.environ['UNDERWORLD_BUILD']=str(build)
    from underworld.native import load_native
    native=load_native()
    commands=[[args.ctest,'--test-dir',str(build),'-C','Release','--output-on-failure'],[sys.executable,'-m','unittest','discover','-s','tests','-v']]
    report={'kind':'living-world-d-regressions','native_build_id':native.build_id,'world_format':native.world_format,'checks':[]}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    for command in commands:
        start=time.perf_counter()
        try:result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=args.timeout)
        except subprocess.TimeoutExpired as e:
            def text(x):return x.decode(errors='replace') if isinstance(x,bytes) else (x or '')
            result=subprocess.CompletedProcess(command,124,text(e.stdout),text(e.stderr)+'\nTIMEOUT')
        report['checks'].append(dict(command=command,returncode=result.returncode,wall_s=time.perf_counter()-start,stdout=result.stdout,stderr=result.stderr))
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
        if result.returncode:return 1
    protected=json.loads((ROOT/'artifacts/stabilization_registration.json').read_text())['phase9_files_sha256']
    report['phase9_hashes_match']={name:hashlib.sha256((ROOT/Path(name.replace('\\','/'))).read_bytes()).hexdigest()==value for name,value in protected.items()}
    report['passed']=all(report['phase9_hashes_match'].values())
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__=='__main__':sys.exit(main())
