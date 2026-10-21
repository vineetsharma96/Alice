"""Packaged G archive bundle, nondefault model guard and read-only viewers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    args.directory.mkdir(parents=True,exist_ok=False);directory=args.directory.resolve();source=args.source.resolve()
    path=directory/'G world.sqlite';exe=ROOT/'dist/UnderworldLab.exe'
    a=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);b=sqlite3.connect(path)
    try:a.backup(b)
    finally:a.close();b.close()
    shutil.copytree(Path(str(source)+'.epochs'),Path(str(path)+'.epochs'))
    clean=os.environ.copy()
    for key in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','UNDERWORLD_BUILD','UNDERWORLD_TOOLCHAIN'):clean.pop(key,None)
    clean['PATH']=str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    clean['UNDERWORLD_TOOLCHAIN']=str(directory/'absent-toolchain');report={'checks':[],'source':str(source)}
    def run(command,expected=0):
        start=time.perf_counter();r=subprocess.run([str(exe),*map(str,command)],env=clean,cwd=directory,capture_output=True,text=True,timeout=90)
        row={'command':list(map(str,command)),'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'wall_s':time.perf_counter()-start};report['checks'].append(row)
        assert r.returncode==expected,row
        return r
    cli=lambda command:json.loads(run(['--cli',*command]).stdout)
    cli(['living-world','archives','--db',path])
    cli(['living-world','task','--db',path,'--agent','agent-4','--goal','inspect_problem','--params','{"target":"resource-1"}','--task-mode','model_assisted'])
    before=cli(['inspect','--db',path])['state_hash']
    rejected=run(['--db',path,'--seconds','0','--port','0','--no-browser','--exit-after-run'],expected=2)
    assert 'model-off' in rejected.stderr
    assert before==cli(['inspect','--db',path])['state_hash']
    cli(['living-world','cancel-task','--db',path,'--agent','agent-4'])
    cli(['living-world','archive','--db',path])
    bundled=directory/'portable.sqlite'
    saved=cli(['save','--db',path,'--name','g-package-save','--output',bundled,'--with-archives'])
    assert saved['archive_files']>0
    cli(['living-world','archives','--db',bundled]);assert cli(['replay','--db',bundled])['replay_matches']
    process=subprocess.Popen([str(exe),'--db',str(path),'--seconds','0','--port','0','--no-browser'],env=clean,cwd=directory,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        ready=json.loads(process.stdout.readline());assert ready['model_calls_enabled'] is False
        r=subprocess.run(['node','scripts/verify_integrated_viewer.mjs',ready['url'],str(ROOT/'artifacts/living_world_g_viewer')],cwd=ROOT,capture_output=True,text=True,timeout=90)
        report['browser']={'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr};assert r.returncode==0,report['browser']
    finally:
        subprocess.run([str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/taskkill.exe'),'/PID',str(process.pid),'/T','/F'],capture_output=True)
        process.wait(timeout=15)
    report.update(passed=True,external_runtime_on_path=False,nondefault_model_task_refused=True,portable_archives_verified=True)
    args.evidence.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','browser')},indent=2))


if __name__=='__main__':main()
