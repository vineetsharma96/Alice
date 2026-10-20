"""Seal the viewer sources separately from the unchanged durable-world runtime."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def build():
    paths=[ROOT/'underworld'/name for name in ('observer.py','viewer.py','__main__.py')]
    paths.extend(ROOT/'underworld/web'/name for name in ('viewer.html','viewer.css','viewer.js','scene.js'))
    paths.extend(sorted((ROOT/'underworld/web/vendor').iterdir()))
    files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    manifest={'schema_version':1,'viewer_protocol':'underworld.viewer/1','three_version':'0.180.0','files':files}
    manifest['source_build_id']=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return manifest


if __name__=='__main__':
    manifest=build();(ROOT/'artifacts/phase8_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(manifest['source_build_id'])
