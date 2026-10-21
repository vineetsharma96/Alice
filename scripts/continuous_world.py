"""Keep an existing model-off world advancing until stopped or a native guard stops it.

Runs committed segments without an overall time limit. Never initializes a save,
resets bodies, replenishes resources or bypasses persistence/native quotas.
"""
import argparse
import json
import math
from pathlib import Path
import signal
import sqlite3
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from underworld import stabilization, storage  # noqa: E402
from underworld.app import validate_model_off  # noqa: E402
from underworld.lease import Lease  # noqa: E402


def emit(value):
    print(json.dumps(value), flush=True)


def run(path, stop, segment_seconds=30, wall_seconds=240, stop_file=None):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('continuous runner requires an existing saved world')
    for value in (segment_seconds, wall_seconds):
        if not math.isfinite(value) or not 0 < value <= 3600:
            raise ValueError('internal segment budgets must be in (0,3600]')
    def stopping():
        return stop.is_set() or (stop_file is not None and Path(stop_file).exists())
    with Lease(path):
        validate_model_off(path)
        initial = storage.inspect(path)
        emit({'continuous': True, 'db': str(path), 'initial_tick': initial['tick'],
              'initial_simulated_s': initial['simulated_time_s'], 'overall_time_limit': None})
        while not stopping():
            current = storage.inspect(path)
            if not any(e['kind'] == 'actor' and e['alive'] and e.get('present', True)
                       for e in current['entities']):
                return {'status': 'population_extinct', 'tick': current['tick']}
            result = stabilization.run(path, segment_seconds, wall_seconds,
                                       stop_requested=stopping)
            emit({'segment': result})
            if not result['replay']['replay_matches']:
                raise RuntimeError('replay mismatch; continuous execution stopped')
            if result['status'] not in ('target_reached', 'wall_limit'):
                return result
            if result['simulated_s'] <= 0:
                raise RuntimeError('no committed progress; continuous execution stopped')
        return {'status': 'stopped', 'tick': storage.inspect(path)['tick']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--stop-file', type=Path, help='default: DB.continuous-stop; create it to stop between committed ticks')
    args = parser.parse_args()
    stop = threading.Event()
    for kind in (signal.SIGINT, signal.SIGTERM):
        signal.signal(kind, lambda *_: stop.set())
    try:
        result = run(args.db, stop, stop_file=args.stop_file or Path(str(args.db) + '.continuous-stop'))
        emit({'finished': result})
        return 0 if result['status'] in ('stopped', 'population_extinct') else 2
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as error:
        emit({'finished': {'status': 'error', 'error': str(error)}})
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
