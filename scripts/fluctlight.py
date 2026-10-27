"""Create and inspect private fluctlight sidecars without changing a world save."""
import argparse
import json
from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from underworld import fluctlight, life_store, weather_store


def read_profile(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def write_profile(path, profile):
    fluctlight.validate(profile)
    Path(path).write_text(json.dumps(profile, indent=2, sort_keys=True), encoding='utf8')


def observation(path, agent):
    with closing(weather_store.connect(path)) as db:
        db.execute('BEGIN')
        world, _, _, _ = getattr(life_store, 'head')(db)
        return world.observe_batch([agent])[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('new'); new.add_argument('--id', required=True); new.add_argument('--output', type=Path, required=True)
    new.add_argument('--role', choices=('inhabitant', 'teacher'), default='inhabitant'); new.add_argument('--seed', type=int, default=0)
    boot = sub.add_parser('bootstrap'); boot.add_argument('--world', type=Path, required=True); boot.add_argument('--agent', required=True)
    boot.add_argument('--output', type=Path, required=True); boot.add_argument('--role', choices=('inhabitant', 'teacher'), default='teacher')
    obs = sub.add_parser('observe'); obs.add_argument('--profile', type=Path, required=True); obs.add_argument('--world', type=Path, required=True); obs.add_argument('--agent', required=True)
    cal = sub.add_parser('calendar'); cal.add_argument('--seconds', type=float, required=True)
    args = parser.parse_args()
    if args.command == 'new':
        write_profile(args.output, fluctlight.new_profile(args.id, role=args.role, seed=args.seed)); return
    if args.command == 'bootstrap':
        profile = fluctlight.new_profile(args.agent+'-fluctlight', role=args.role, native_observer_id=args.agent)
        write_profile(args.output, fluctlight.observe(profile, observation(args.world, args.agent))); return
    if args.command == 'observe':
        write_profile(args.profile, fluctlight.observe(read_profile(args.profile), observation(args.world, args.agent))); return
    print(json.dumps(fluctlight.calendar(args.seconds), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
