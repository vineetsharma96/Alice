"""Opt-in weather new/run/save/resume/inspect commands; no old-world migration."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import weather_store as store  # noqa: E402
from underworld.weather_runtime import climate, configuration  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['new', 'run', 'inspect', 'save', 'replay', 'policy-step', 'force'])
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--seed', type=int, default=53)
    parser.add_argument('--population', type=int, default=4)
    parser.add_argument('--ticks', type=int, default=40)
    parser.add_argument('--year-seconds', type=float, default=2400)
    parser.add_argument('--disabled', action='store_true')
    parser.add_argument('--guided', action='store_true')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--agent', default='agent-1')
    parser.add_argument('--policy', choices=['weather','survival'], default='weather')
    parser.add_argument('--assign', choices=['build_simple_shelter','repair_shelter','prepare_supplies'])
    parser.add_argument('--payload', type=Path)
    args = parser.parse_args()
    if args.command == 'new':
        if args.config and (args.disabled or args.year_seconds != 2400):
            parser.error('Use either --config or climate override flags')
        settings = configuration(args.config) if args.config else climate(enabled=not args.disabled, year_s=args.year_seconds)
        result = store.initialize(args.db, args.seed, args.population, settings, args.guided)
    elif args.command == 'run':
        store.commit(args.db, dict(kind='step', ticks=args.ticks))
        result = store.inspect(args.db)
    elif args.command == 'save':
        if not args.destination:parser.error('save requires --destination')
        result = store.save(args.db, args.destination)
    elif args.command == 'replay':result = store.replay(args.db)
    elif args.command == 'policy-step':
        command=dict(kind='policy',agent=args.agent,mode=args.policy)
        if args.assign:command['assignment']=dict(goal=args.assign)
        result=store.commit(args.db,command)
    elif args.command == 'force':
        if not args.payload:parser.error('force requires explicit --payload JSON with id, native observation_version and duration')
        result=store.commit(args.db,dict(kind='force',parameters=json.loads(args.payload.read_text(encoding='utf8'))))
    else:result = store.inspect(args.db)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':main()
