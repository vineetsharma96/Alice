"""Attach, advance, inspect, save and replay a connected living-world copy."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from underworld import living_world_bridge as bridge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    attach = sub.add_parser("attach")
    attach.add_argument("--source", type=Path, required=True)
    attach.add_argument("--db", type=Path, required=True)
    attach.add_argument("--biological-step-s", type=float, default=86400.0)
    attach.add_argument("--mode", choices=("connected", "frozen"), default="connected")

    run = sub.add_parser("run")
    run.add_argument("--db", type=Path, required=True)
    run.add_argument("--ticks", type=int, required=True)
    run.add_argument("--output", type=Path, required=True)

    for name in ("inspect", "replay"):
        item = sub.add_parser(name)
        item.add_argument("--db", type=Path, required=True)

    save = sub.add_parser("save")
    save.add_argument("--db", type=Path, required=True)
    save.add_argument("--destination", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "attach":
        result = bridge.attach(
            args.source,
            args.db,
            biological_step_s=args.biological_step_s,
            mode=args.mode,
        )
    elif args.command == "run":
        if args.output.exists():
            parser.error("refuse overwriting living bridge evidence")
        result = bridge.run(args.db, args.ticks)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    elif args.command == "inspect":
        result = bridge.inspect(args.db)
    elif args.command == "replay":
        result = bridge.replay(args.db)
    else:
        result = bridge.save(args.db, args.destination)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
