"""Progressive, no-reset population runs under the registered life protocol."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import life_store as store,weather_store as weather
from scripts.life import run
from scripts.life_experiment import SEEDS


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.folder.exists() or a.output.exists():p.error('Use unused evidence paths')
    a.folder.mkdir(parents=True);results=[]
    for seed,population in [(s,4) for s in SEEDS]+[(61,8)]:
        source=a.folder/f'{seed}-{population}-source.sqlite';path=a.folder/f'{seed}-{population}-life.sqlite'
        store.initialize_source(source,seed=seed,population=population)
        original=hashlib.sha256(source.read_bytes()).hexdigest();store.attach(source,path)
        result=dict(seed=seed,population=population,world=str(path.resolve()),segments=[])
        try:
            for until in ((30,90,180) if population==4 else (90,)):
                segment=run(path,until);result['segments'].append(segment)
                if segment['status']!='target_reached':break
            backup=a.folder/f'{seed}-{population}-backup.sqlite';weather.save(path,backup)
            child=subprocess.run([sys.executable,'-c','from underworld.life_store import replay;import json,sys;print(json.dumps(replay(sys.argv[1])))',str(backup)],cwd=ROOT,capture_output=True,text=True,check=True)
            result['fresh_process_replay']=json.loads(child.stdout)
            result['backup_equal']=store.inspect(path)['hash']==store.inspect(backup)['hash']
            result['source_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==original
        except Exception as error:result['error']=repr(error)
        results.append(result);a.output.write_text(json.dumps(dict(protocol='docs/LIFE_INTEGRATION_PROTOCOL.md',runs=results),indent=2),encoding='utf8')
        print(json.dumps(dict(seed=seed,population=population,alive=result['segments'][-1]['alive'] if result['segments'] else None,error=result.get('error'))),flush=True)


if __name__=='__main__':main()
