"""Capture and inspect native ALICE-LIFE-2 body-need snapshots."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase3 as phase3


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
    body_needs = sub.add_parser('body-needs')
    body_needs.add_argument('--db', type=Path, required=True)
    body_needs.add_argument('--agent')
    body_need = sub.add_parser('body-need')
    body_need.add_argument('--db', type=Path, required=True)
    body_need.add_argument('--body-need-id', required=True)
    save = sub.add_parser('save')
    save.add_argument('--db', type=Path, required=True)
    save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach':
        result = phase3.attach(args.source, args.db)
    elif args.command == 'capture':
        result = phase3.capture(args.db, agents=args.agents)
    elif args.command == 'inspect':
        result = phase3.inspect(args.db)
    elif args.command == 'replay':
        result = phase3.replay(args.db)
    elif args.command == 'body-needs':
        result = phase3.body_needs(args.db, agent_id=args.agent)
    elif args.command == 'body-need':
        result = phase3.body_need(args.db, args.body_need_id)
    else:
        result = phase3.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
