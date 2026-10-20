"""Exercise F knowledge CLI and actual injection forms in the packaged runtime."""
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True,help='completed F confirmation SQLite backup')
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=False);directory=args.directory.resolve()
    exe=ROOT/'dist/UnderworldLab.exe';clean=os.environ.copy()
    for key in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','UNDERWORLD_BUILD','UNDERWORLD_TOOLCHAIN'):clean.pop(key,None)
    clean['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    clean['UNDERWORLD_TOOLCHAIN']=str(directory/'absent-toolchain')
    report={'checks':[]}
    def run(command):
        started=time.perf_counter()
        r=subprocess.run([str(exe),'--cli',*map(str,command)],env=clean,cwd=directory,capture_output=True,text=True,timeout=90)
        report['checks'].append({'command':list(map(str,command)),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'wall_s':time.perf_counter()-started})
        assert r.returncode==0,report['checks'][-1]
        return json.loads(r.stdout)
    profile=directory/'profile.sqlite'
    run(['living-world','init','--db',profile,'--calls','0','--knowledge-profile','woodcraft','--knowledge-recipient','agent-1'])
    assert run(['knowledge','--db',profile,'--agent','agent-1'])['counts']['external_initialization']==1
    assert run(['knowledge','--db',profile,'--agent','agent-2'])['counts']['external_initialization']==0
    path=directory/'UI copied world.sqlite'
    source=sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro',uri=True)
    target=sqlite3.connect(path)
    try:source.backup(target)
    finally:source.close();target.close()
    assert run(['replay','--db',path])['replay_matches']
    process=subprocess.Popen([str(exe),'--cli','observe','--db',str(path),'--port','0'],env=clean,cwd=directory,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        ready=process.stdout.readline();url=re.search(r'http://127.0.0.1:\d+/viewer',ready)
        assert url,ready
        result=subprocess.run(['node','scripts/verify_knowledge_viewer.mjs',url[0],str(ROOT/'artifacts/living_world_f_viewer')],cwd=ROOT,capture_output=True,text=True,timeout=90)
        report['browser']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
        assert result.returncode==0,report['browser']
    finally:
        subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],capture_output=True)
        process.wait(timeout=15)
    assert run(['replay','--db',path])['replay_matches']
    report.update(passed=True,external_runtime_on_path=False)
    args.evidence.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'external_runtime_on_path':False}))


if __name__=='__main__':main()
