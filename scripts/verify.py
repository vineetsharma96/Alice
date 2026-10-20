"""Compatibility verifier entry point; never replace Phase 9 evidence."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--core',type=Path,required=True)
    p.add_argument('--ctest',default='ctest')
    p.add_argument('--timeout',type=int,default=420)
    p.add_argument('--output',type=Path)
    args=p.parse_args();core=args.core.resolve()
    build=core.parent if (core.parent/'CMakeCache.txt').exists() else core.parent.parent
    output=args.output or ROOT/'artifacts'/f'verification-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex}.json'
    return subprocess.call([sys.executable,str(ROOT/'scripts/verify_living_world.py'),'--build',str(build),
                            '--ctest',args.ctest,'--timeout',str(args.timeout),'--output',str(output)],cwd=ROOT)


if __name__=='__main__':raise SystemExit(main())
