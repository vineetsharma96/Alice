"""Command-line surface for the durable, copy-only F8 regulation overlay."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import regulation_store_f8 as store


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    attach = sub.add_parser("attach")
    attach.add_argument("source", type=Path)
    attach.add_argument("destination", type=Path)
    for name in ("inspect", "replay", "resume"):
        command = sub.add_parser(name)
        command.add_argument("db", type=Path)
    save = sub.add_parser("save")
    save.add_argument("db", type=Path)
    save.add_argument("destination", type=Path)
    choose = sub.add_parser("choose")
    choose.add_argument("db", type=Path)
    choose.add_argument("owner")
    choose.add_argument("candidates", type=Path)
    record = sub.add_parser("record-outcome")
    record.add_argument("db", type=Path)
    record.add_argument("owner")
    record.add_argument("before", type=Path)
    record.add_argument("outcome", type=Path)
    record.add_argument("--after", type=Path)
    record.add_argument("--operation-id")
    current = sub.add_parser("record-current")
    current.add_argument("db", type=Path)
    current.add_argument("owner")
    current.add_argument("before", type=Path)
    current.add_argument("outcome", type=Path)
    current.add_argument("--operation-id")
    args = parser.parse_args(argv)
    if args.command == "attach":
        result = store.attach(args.source, args.destination)
    elif args.command == "inspect":
        result = store.inspect(args.db)
    elif args.command == "replay":
        result = store.replay(args.db)
    elif args.command == "resume":
        result = store.resume(args.db)
    elif args.command == "save":
        result = store.save(args.db, args.destination)
    elif args.command == "choose":
        result = store.choose(args.db, args.owner, _read(args.candidates))
    elif args.command == "record-outcome":
        after = None if args.after is None else _read(args.after)
        result = store.record_outcome(args.db, args.owner, _read(args.before),
                                      _read(args.outcome), after=after,
                                      operation_id=args.operation_id)
    else:
        result = store.record_current_outcome(args.db, args.owner, _read(args.before),
                                              _read(args.outcome),
                                              operation_id=args.operation_id)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
