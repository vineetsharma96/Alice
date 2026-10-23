"""Small command-line surface for the additive F6 relationship store."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import relationship_store_f6 as store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    attach = sub.add_parser("attach")
    attach.add_argument("source", type=Path)
    attach.add_argument("destination", type=Path)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("db", type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("db", type=Path)
    save = sub.add_parser("save")
    save.add_argument("db", type=Path)
    save.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    if args.command == "attach":
        result = store.attach(args.source, args.destination)
    elif args.command == "inspect":
        result = store.inspect(args.db)
    elif args.command == "replay":
        result = store.replay(args.db)
    else:
        result = store.save(args.db, args.destination)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
