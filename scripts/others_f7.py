"""Command-line surface for the additive F7 inference store."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import others_store_f7 as store


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
    record = sub.add_parser("record-observation")
    record.add_argument("db", type=Path)
    record.add_argument("observer")
    record.add_argument("envelope", type=Path,
                        help="JSON file containing the strict public F7 envelope")
    record.add_argument("--native-observation", type=Path,
                        help="JSON file containing the observer's current native observation")
    record.add_argument("--operation-id")
    current = sub.add_parser("record-current")
    current.add_argument("db", type=Path)
    current.add_argument("observer")
    current.add_argument("target")
    current.add_argument("--operation-id")
    args = parser.parse_args(argv)
    if args.command == "attach":
        result = store.attach(args.source, args.destination)
    elif args.command == "inspect":
        result = store.inspect(args.db)
    elif args.command == "replay":
        result = store.replay(args.db)
    elif args.command == "save":
        result = store.save(args.db, args.destination)
    elif args.command == "record-observation":
        envelope = json.loads(args.envelope.read_text(encoding="utf-8"))
        native = None
        if args.native_observation is not None:
            native = json.loads(args.native_observation.read_text(encoding="utf-8"))
        result = store.record_observation(args.db, args.observer, native, envelope,
                                          operation_id=args.operation_id)
    else:
        result = store.record_current_observation(args.db, args.observer, args.target,
                                                  operation_id=args.operation_id)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
