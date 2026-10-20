"""Vendor the pinned MIT browser renderer. No package installation or runtime CDN."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'underworld/web/vendor'
PIN='r180'
FILES={'three.module.min.js':'build/three.module.min.js','three.core.min.js':'build/three.core.min.js',
       'OrbitControls.js':'examples/jsm/controls/OrbitControls.js','LICENSE.three':'LICENSE'}


def main():
    DEST.mkdir(exist_ok=True);manifest={'version':'0.180.0','tag':PIN,'license':'MIT','files':{}}
    for name,source in FILES.items():
        url=f'https://raw.githubusercontent.com/mrdoob/three.js/{PIN}/{source}'
        with urlopen(url,timeout=30) as response:raw=response.read(3*1024*1024)
        original=hashlib.sha256(raw).hexdigest()
        if name=='OrbitControls.js':raw=raw.replace(b"from 'three'",b"from './three.module.min.js'")
        target=DEST/name
        if target.exists() and target.read_bytes()!=raw:raise ValueError('refusing to overwrite different vendored file: '+name)
        target.write_bytes(raw)
        manifest['files'][name]={'source':url,'source_sha256':original,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    (DEST/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Vendored Three.js',manifest['version'],sum(f['bytes'] for f in manifest['files'].values()),'bytes; MIT license retained')


if __name__=='__main__':main()
