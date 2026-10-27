"""Build a Windows model-off executable; never bundle user worlds/models/secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,default=ROOT/'build/living-d')
    p.add_argument('--evidence',type=Path,default=ROOT/'artifacts/package_app.json')
    args=p.parse_args()
    if os.name!='nt':p.error('This packaging recipe is verified for Windows only; run.sh supports source builds elsewhere.')
    build=args.build.resolve();os.environ['UNDERWORLD_BUILD']=str(build)
    sys.path.insert(0,str(ROOT));from underworld.native import load_native
    native=load_native();toolchain=Path(os.environ.get('UNDERWORLD_TOOLCHAIN',r'C:\mingw64\bin'))
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--onefile','--console','--name','UnderworldLab',
             '--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build/packaging'), '--specpath',str(ROOT/'build/packaging'),
             '--paths',str(ROOT),'--paths',str(build),'--paths',str(ROOT/'build/weather'),
             '--hidden-import','_underworld','--hidden-import','_underworld_weather','--hidden-import','underworld.__main__',
             '--hidden-import','underworld.life_control','--hidden-import','underworld.life_viewer']
    bundled_data=set()
    def add_data(relative):
        relative = Path(relative)
        key = relative.as_posix()
        if key in bundled_data or not (ROOT / relative).exists():
            return
        bundled_data.add(key)
        command.extend(['--add-data', f'{ROOT / relative};{relative.parent.as_posix()}'])
    for file in sorted((ROOT/'underworld').glob('*.py')):command += ['--add-data',f'{file};underworld']
    command += ['--add-data',f'{ROOT / "underworld/web"};underworld/web','--add-data',f'{ROOT / "config"};config']
    for relative in ('artifacts/emotion_registration.json', 'artifacts/weather_registration.json',
                     'artifacts/phase9_registration.json', 'docs/PHASE9_PREREGISTRATION.md'):
        add_data(relative)
    for registration in ('artifacts/emotion_registration.json', 'artifacts/weather_registration.json'):
        manifest = json.loads((ROOT / registration).read_text(encoding='utf8'))
        for relative in manifest.get('files', {}):
            if not relative.startswith(('underworld/', 'config/')):
                add_data(relative)
    for name in ('libgcc_s_seh-1.dll','libstdc++-6.dll','libwinpthread-1.dll'):
        file=toolchain/name
        if file.exists():command+=['--add-binary',f'{file};.']
    command += [str(ROOT/'scripts/desktop_entry.py')]
    subprocess.run(command,cwd=ROOT,check=True)
    exe=ROOT/'dist/UnderworldLab.exe'
    report={'executable':str(exe),'bytes':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
            'native_build_id':native.build_id,'command':command,'platform':sys.platform,'python':sys.version,
            'note':'Unsigned Windows build; model-off desktop path, no bundled worlds/models/environment files. AppContainer runner requires source runtime.'}
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
