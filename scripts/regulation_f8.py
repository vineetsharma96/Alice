"""Command-line surface for the pure, bounded F8 regulation slice."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from underworld import regulation_f8 as regulation


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_json(value):
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    initial = sub.add_parser("initial", help="print an empty learner state")
    initial.add_argument("owner")
    initial.add_argument("run_id")

    choose = sub.add_parser("choose", help="choose from JSON observation/state/candidates files")
    choose.add_argument("observation", type=Path)
    choose.add_argument("state", type=Path)
    choose.add_argument("candidates", type=Path)

    outcome = sub.add_parser("outcome", help="learn from JSON state/before/after/outcome files")
    outcome.add_argument("state", type=Path)
    outcome.add_argument("before", type=Path)
    outcome.add_argument("after", type=Path)
    outcome.add_argument("outcome", type=Path)

    args = parser.parse_args(argv)
    if args.command == "initial":
        result = regulation.initial(args.owner, args.run_id)
    elif args.command == "choose":
        result = regulation.choose(
            _read_json(args.observation),
            _read_json(args.state),
            _read_json(args.candidates),
        )
    else:
        state = _read_json(args.state)
        evidence = regulation.observe_outcome(
            state,
            _read_json(args.before),
            _read_json(args.after),
            _read_json(args.outcome),
        )
        result = {"evidence": evidence, "state": state}
    _print_json(result)


if __name__ == "__main__":
    main()
