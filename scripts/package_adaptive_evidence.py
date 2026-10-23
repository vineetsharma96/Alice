"""Package exact traces; exercise audit refusal without modifying scored saves."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.adaptive_audit import audit, read  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def negative_checks():
    original = read(ROOT / 'artifacts/gap_confirmation.json')
    registration = ROOT / 'artifacts/gap_registration.json'
    results = {}
    with tempfile.TemporaryDirectory(prefix='gap-audit-negative-') as directory:
        temporary = Path(directory)
        for name in ('false_goal', 'false_receipt', 'missing_world', 'changed_registration'):
            report = copy.deepcopy(original)
            pins = read(registration)
            if name == 'false_goal':
                trial = report['runs'][0]['online']['adaptive']['heldout'][0]
                trial['success'] = not trial['success']
            elif name == 'false_receipt':
                report['runs'][0]['online']['adaptive']['training'][0]['receipt']['status'] = 'fabricated'
            elif name == 'missing_world':
                report['runs'][0]['directory'] = str(temporary / 'absent')
            else:
                pins['files']['underworld/adaptive.py'] = '0' * 64
            study = temporary / 'study.json'
            pin_path = temporary / 'pins.json'
            study.write_text(json.dumps(report), encoding='utf8')
            pin_path.write_text(json.dumps(pins), encoding='utf8')
            try:
                audit(study, pin_path)
            except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
                results[name] = dict(refused=True, reason=str(error))
            else:
                raise AssertionError('audit accepted ' + name)
    return results


def main():
    negative = negative_checks()
    archives = []
    for name in ('gap_confirmation', 'gap_development', 'gap_development2', 'gap_development3',
                 'gap_development4', 'gap_teaching_development', 'gap_continuity_dev_init',
                 'gap_continuity_dev_300', 'gap_continuity_dev_900', 'gap_continuity_dev_1800',
                 'gap_continuity_control'):
        path = ROOT / 'artifacts' / (name + '.json')
        raw = path.read_bytes()
        packed = gzip.compress(raw, mtime=0)
        assert gzip.decompress(packed) == raw
        destination = path.with_suffix('.json.gz')
        if destination.exists():
            assert destination.read_bytes() == packed
        else:
            destination.write_bytes(packed)
        archives.append(dict(raw=str(path.relative_to(ROOT)).replace('\\', '/'),
                             archive=str(destination.relative_to(ROOT)).replace('\\', '/'),
                             raw_bytes=len(raw), archive_bytes=len(packed),
                             raw_sha256=digest(raw), archive_sha256=digest(packed)))
    worlds = []
    paths = sorted((ROOT / 'data/gap-confirmation-20261021').glob('*.sqlite'))
    paths += [ROOT / 'data/gap-continuity-dev-20261021.sqlite']
    paths += sorted((ROOT / 'data/gap-continuity-control-20261021').glob('*.sqlite'))
    for path in paths:
        worlds.append(dict(path=str(path.relative_to(ROOT)).replace('\\', '/'),
                           bytes=path.stat().st_size, sha256=digest(path.read_bytes())))
    result = dict(archives=archives, negative_checks=negative, native_worlds=worlds,
                  supplemental_source_hashes={p: digest((ROOT / p).read_bytes()) for p in
                                             ['scripts/package_adaptive_evidence.py', 'scripts/adaptive_control.py',
                                              'scripts/adaptive_continuity_audit.py']},
                  scope='Exact compressed traces are portable. Actual SQLite saves remain local ignored data; hashes are inventory, not exported saves.')
    (ROOT / 'artifacts/gap_evidence_archives.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps(dict(archives=len(archives), native_worlds=len(worlds), negative_checks=negative)))


if __name__ == '__main__':
    main()
