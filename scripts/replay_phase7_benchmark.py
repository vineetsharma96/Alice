"""Read-only replay with the captured benchmark runtime, never rewriting run identities."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--db',required=True,type=Path);args=parser.parse_args()
snapshot=ROOT/'artifacts/phase7_benchmark_runtime'
manifest=json.loads((snapshot/'manifest.json').read_text(encoding='utf-8'))
for name,expected in manifest['files'].items():
    if hashlib.sha256((snapshot/'underworld'/name).read_bytes()).hexdigest()!=expected:raise ValueError('captured runtime checksum mismatch: '+name)
sys.path.insert(0,str(snapshot));os.environ.setdefault('UNDERWORLD_BUILD',str(ROOT/'build'))
from underworld import storage
if storage.orchestration_id()!=manifest['orchestration_id'] or storage.load_native().build_id!=manifest['native_build_id']:raise ValueError('benchmark native/runtime identity mismatch')
print(json.dumps(storage.replay(args.db.resolve()),indent=2))
