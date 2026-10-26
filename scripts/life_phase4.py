"""Capture and inspect private ALICE-LIFE-2 affect and mood traces."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase4 as phase4


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
    traces = sub.add_parser('affect-traces')
    traces.add_argument('--db', type=Path, required=True)
    traces.add_argument('--agent')
    trace = sub.add_parser('affect-trace')
    trace.add_argument('--db', type=Path, required=True)
    trace.add_argument('--affect-trace-id', required=True)
    save = sub.add_parser('save')
    save.add_argument('--db', type=Path, required=True)
    save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach':
        result = phase4.attach(args.source, args.db)
    elif args.command == 'capture':
        result = phase4.capture(args.db, agents=args.agents)
    elif args.command == 'inspect':
        result = phase4.inspect(args.db)
    elif args.command == 'replay':
        result = phase4.replay(args.db)
    elif args.command == 'affect-traces':
        result = phase4.affect_traces(args.db, agent_id=args.agent)
    elif args.command == 'affect-trace':
        result = phase4.affect_trace(args.db, args.affect_trace_id)
    else:
        result = phase4.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
