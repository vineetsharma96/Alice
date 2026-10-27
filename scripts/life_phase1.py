"""Attach, capture, inspect, replay and back up Phase-1 ALICE-LIFE-2 records."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase1 as phase1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    attach = sub.add_parser('attach')
    attach.add_argument('--source', type=Path, required=True)
    attach.add_argument('--db', type=Path, required=True)
    attach.add_argument('--agents', nargs='*')
    attach.add_argument('--mode', default='connected')
    capture = sub.add_parser('capture')
    capture.add_argument('--db', type=Path, required=True)
    capture.add_argument('--agents', nargs='*')
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--db', type=Path, required=True)
    observations = sub.add_parser('observations')
    observations.add_argument('--db', type=Path, required=True)
    observations.add_argument('--agent')
    replay = sub.add_parser('replay')
    replay.add_argument('--db', type=Path, required=True)
    save = sub.add_parser('save')
    save.add_argument('--db', type=Path, required=True)
    save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach':
        result = phase1.attach(args.source, args.db, agents=args.agents, mode=args.mode)
    elif args.command == 'capture':
        result = phase1.capture(args.db, agents=args.agents)
    elif args.command == 'inspect':
        result = phase1.inspect(args.db)
    elif args.command == 'observations':
        result = phase1.observations(args.db, agent_id=args.agent)
    elif args.command == 'replay':
        result = phase1.replay(args.db)
    else:
        result = phase1.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
