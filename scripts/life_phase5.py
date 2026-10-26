"""Capture and inspect unified ALICE-LIFE-2 lineage snapshots."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase5 as phase5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    attach = sub.add_parser('attach')
    attach.add_argument('--source', type=Path, required=True)
    attach.add_argument('--db', type=Path, required=True)
    capture = sub.add_parser('capture')
    capture.add_argument('--db', type=Path, required=True)
    capture.add_argument('--agents', nargs='*')
    for name in ('inspect', 'replay'):
        command = sub.add_parser(name)
        command.add_argument('--db', type=Path, required=True)
    snapshots = sub.add_parser('snapshots')
    snapshots.add_argument('--db', type=Path, required=True)
    snapshots.add_argument('--agent')
    snapshot = sub.add_parser('snapshot')
    snapshot.add_argument('--db', type=Path, required=True)
    snapshot.add_argument('--snapshot-id', required=True)
    save = sub.add_parser('save')
    save.add_argument('--db', type=Path, required=True)
    save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach':
        result = phase5.attach(args.source, args.db)
    elif args.command == 'capture':
        result = phase5.capture(args.db, agents=args.agents)
    elif args.command == 'inspect':
        result = phase5.inspect(args.db)
    elif args.command == 'replay':
        result = phase5.replay(args.db)
    elif args.command == 'snapshots':
        result = phase5.snapshots(args.db, agent_id=args.agent)
    elif args.command == 'snapshot':
        result = phase5.snapshot(args.db, args.snapshot_id)
    else:
        result = phase5.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
