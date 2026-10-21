"""Check delivery evidence and full cohort inventory without advancing a world.

This post-measurement inventory adds no policy changes or experimental thresholds.
Its software checks are separate from the measured, partial pen integration.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8-sig'))


def main():
    summary = read('artifacts/living_world_g_summary.json')
    registration = read('artifacts/living_world_g_registration.json')
    runs = summary['runs']
    checks = read('artifacts/living_world_g_checks.json')
    package = read('artifacts/living_world_g_package.json')
    extension = read('artifacts/living_world_g_extension.json')
    phase9 = read('artifacts/living_world_g_phase9_audit.json')
    executable_hash = hashlib.sha256((ROOT / 'dist/UnderworldLab.exe').read_bytes()).hexdigest()
    archive = ROOT / 'build/runtime-before-milestone-g-20261021'
    old_files = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))['files']
    gates = {
        'exact_four_cell_inventory': len(runs) == 4 and {(r['seed'], r['arm']) for r in runs}
            == {(seed, arm) for seed in (2521, 2549) for arm in ('unassigned', 'assigned')},
        'primary_horizons': all(r['simulated_s'] == 300 and
            [s['actual_simulated_s'] for s in r['stages']] == [60, 300] and
            all(s['status'] == 'target_reached' for s in r['stages']) for r in runs),
        'registered_sources_unchanged': len(registration['files']) == 43 and all(
            hashlib.sha256((ROOT / n).read_bytes()).hexdigest() == h
            for n, h in registration['files'].items()),
        'software_invariants': summary['software_invariants_pass'],
        'continuity': read('artifacts/living_world_g_continuity.json')['passed'],
        'false_claim_native_rejection': read('artifacts/living_world_g_false_lesson.json')['passed'],
        'full_regressions': checks['passed'] and len(checks['checks']) == 2 and
            all(c['returncode'] == 0 for c in checks['checks']) and
            re.search(r'Ran 239 tests\b', checks['checks'][1]['stderr']) is not None,
        'general_package': read('artifacts/living_world_g_package_general.json')['passed'],
        'integrated_package': read('artifacts/living_world_g_package_integration.json')['passed'],
        'both_viewers': read('artifacts/living_world_g_viewer.json')['passed'],
        'bash_launcher': read('artifacts/living_world_g_launcher.json')['passed'],
        'executable_identity': executable_hash == package['sha256'] ==
            read('artifacts/living_world_g_package_general.json')['exe_sha256'] ==
            read('artifacts/living_world_g_launcher.json')['exe_sha256'],
        'pre_g_runtime_unchanged': len(old_files) == 54 and all(
            hashlib.sha256((archive / n).read_bytes()).hexdigest() == h for n, h in old_files.items()),
        'pre_g_saved_world_compatibility': read('artifacts/living_world_g_f_compatibility.json')['passed'],
        'phase9_still_sealed_and_failed': phase9['verified_files'] == 3439 and
            phase9['verified_source_files'] == 4 and phase9['recomputed_metrics_match'] and
            phase9['advance'] is False,
        'extension_replay_and_accounting': extension['replay']['replay_matches'] and
            not any(extension['after']['balances'].values()) and
            extension['initial_simulated_s'] == 300 and extension['final_simulated_s'] == 537,
    }
    report = {
        'verification_passed': all(gates.values()), 'gates': gates,
        'held_out_pens_completed': sum(r['pen_verified'] for r in runs if r['arm'] == 'assigned'),
        'held_out_integration_complete': False,
        'extension_status': extension['run']['status'],
        'extension_simulated_s': extension['final_simulated_s'],
        'extension_wall_s': extension['wall_s'], 'executable_sha256': executable_hash,
        'interpretation': 'Software verification passes independently of partial held-out production. '
            'No full pen or sustained husbandry claim; Phase9 advance remains false.',
    }
    (ROOT / 'artifacts/living_world_g_delivery_audit.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['verification_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
