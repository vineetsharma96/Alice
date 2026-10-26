"""Persist and inspect private ALICE-LIFE-2 memory records."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import life_phase2 as phase2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    attach = sub.add_parser('attach')
    attach.add_argument('--source', type=Path, required=True)
    attach.add_argument('--db', type=Path, required=True)
    write = sub.add_parser('write')
    write.add_argument('--db', type=Path, required=True)
    write.add_argument('--agent', required=True)
    write.add_argument('--memory-id', required=True)
    write.add_argument('--kind', default='episode')
    write.add_argument('--content', type=json.loads, required=True)
    write.add_argument('--source-ref', action='append', required=True)
    write.add_argument('--confidence', type=float, default=0.0)
    write.add_argument('--salience', type=float, default=0.0)
    write.add_argument('--provenance', default='authored')
    write.add_argument('--supersedes')
    invalidate = sub.add_parser('invalidate')
    invalidate.add_argument('--db', type=Path, required=True)
    invalidate.add_argument('--memory-id', required=True)
    for name in ('inspect', 'replay'):
        command = sub.add_parser(name)
        command.add_argument('--db', type=Path, required=True)
    memories = sub.add_parser('memories')
    memories.add_argument('--db', type=Path, required=True)
    memories.add_argument('--agent')
    memories.add_argument('--active-only', action='store_true')
    memory = sub.add_parser('memory')
    memory.add_argument('--db', type=Path, required=True)
    memory.add_argument('--memory-id', required=True)
    save = sub.add_parser('save')
    save.add_argument('--db', type=Path, required=True)
    save.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'attach':
        result = phase2.attach(args.source, args.db)
    elif args.command == 'write':
        result = phase2.write_memory(args.db, agent_id=args.agent, memory_id=args.memory_id,
                                     memory_kind=args.kind, content=args.content,
                                     source_refs=args.source_ref, confidence=args.confidence,
                                     salience=args.salience, provenance=args.provenance,
                                     supersedes=args.supersedes)
    elif args.command == 'invalidate':
        result = phase2.invalidate(args.db, args.memory_id)
    elif args.command == 'inspect':
        result = phase2.inspect(args.db)
    elif args.command == 'replay':
        result = phase2.replay(args.db)
    elif args.command == 'memories':
        result = phase2.memories(args.db, agent_id=args.agent, active_only=args.active_only)
    elif args.command == 'memory':
        result = phase2.memory(args.db, args.memory_id)
    else:
        result = phase2.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
