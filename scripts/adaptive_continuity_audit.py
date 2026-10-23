"""Supplementary read-only audit of the measured continuous gap-profile life."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.adaptive_audit import read, world  # noqa: E402
from underworld import storage  # noqa: E402


def accounting(snapshot):
    assert snapshot['ecology']['forage_regeneration_kg_s'] == 0
    assert snapshot['interventions'] == 0
    assert not any(snapshot['boundary_sources_ug'].values())
    assert not any(snapshot['operator_sources_ug'].values())
    actors = [e for e in snapshot['entities'] if e['kind'] == 'actor']
    assert len(actors) == 4 and all(e['alive'] and e['body']['health'] == 1 for e in actors)
    stocks = {}
    for kind in ('food', 'water'):
        stock = sum(int(e['mass_ug']) for e in snapshot['entities'] if e['kind'] == kind)
        carried = sum(int(e['inventory_ug'].get(kind, 0)) for e in actors)
        consumed = sum(int(e['body'][kind + '_ingested_ug']) for e in actors)
        assert stock + carried + consumed == int(snapshot['material_totals_ug'][kind])
        stocks[kind] = dict(stock_ug=stock, carried_ug=carried, consumed_ug=consumed)
    return stocks


def main():
    initial = read(ROOT / 'artifacts/gap_continuity_dev_init.json')
    previous = initial
    windows = []
    for target in (300, 900, 1800):
        report = read(ROOT / f'artifacts/gap_continuity_dev_{target}.json')
        assert report['initial'] == previous
        before, after = report['initial']['snapshot'], report['final']['snapshot']
        assert before['run_id'] == after['run_id'] == initial['snapshot']['run_id']
        assert after['simulated_time_s'] > before['simulated_time_s']
        assert report['stop_reason'] == 'horizon_reached'
        assert report['operator_interventions'] == 0
        assert report['final']['model_calls'] == 0 and report['final']['replay']['replay_matches']
        stocks = accounting(after)
        assert all(report['final']['audit']['people'][a]['version'] >=
                   report['initial']['audit']['people'][a]['version']
                   for a in initial['audit']['people'])
        windows.append(dict(start_sim_s=before['simulated_time_s'], end_sim_s=after['simulated_time_s'],
                            wall_s=report['wall_s'], frames=report['frames'], stocks=stocks))
        previous = report['final']
    root_path = ROOT / 'data/gap-continuity-dev-20261021.sqlite'
    world(root_path, previous)
    control = read(ROOT / 'artifacts/gap_continuity_control.json')
    # The supplement adds genuinely observed legacy memories to BOTH copies;
    # native bodies/head must remain exactly the 1806-second continuing life.
    assert control['initial']['snapshot'] == previous['snapshot']
    common = ROOT / 'data/gap-continuity-control-20261021/common.sqlite'
    world(common, control['initial'])
    controls = {}
    for mode, report in control['runs'].items():
        path = ROOT / report['path']
        world(path, report['final'])
        after = report['final']['snapshot']
        assert after['run_id'] == initial['snapshot']['run_id']
        assert report['operator_interventions'] == 0 and report['stop_reason'] == 'horizon_reached'
        with closing(storage._connect(path, readonly=True)) as db:
            operators = db.execute("SELECT COUNT(*) FROM decisions WHERE source IN ('operator','operator_knowledge')").fetchone()[0]
            assert operators == 0
        controls[mode] = dict(end_sim_s=after['simulated_time_s'], wall_s=report['wall_s'],
                              goals=report['new_completed_goals'], frames=report['frames'], stocks=accounting(after))
    result = dict(verified=True, windows=windows, controls=controls,
                  final_goals={a: p['adaptive']['goals'] for a, p in previous['audit']['people'].items()},
                  continuing_wall_s=sum(x['wall_s'] for x in windows), model_calls=0,
                  source_hashes={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                                 ['scripts/adaptive_control.py', 'scripts/adaptive_continuity_audit.py']},
                  scope='one development life; no demonstrated survival advantage; not indefinite or multi-seed survival')
    (ROOT / 'artifacts/gap_continuity_audit.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
