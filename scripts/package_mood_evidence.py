"""Archive frozen F4 source and checksums without changing experimental results."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def main():
    r=json.loads((ROOT/'artifacts/mood_f4_registration.json').read_text(encoding='utf8'))
    archive=ROOT/'artifacts/mood_f4_frozen_sources.zip'
    extras=[ROOT/'CMakeLists.txt']+list((ROOT/'core').glob('*'))
    extras += [ROOT/'artifacts'/f'{n}.json' for n in ['living_world_g_registration','developmental_h1_registration_repaired',
               'developmental_h2_registration','h3_native_registration','h4_registration','h5_registration',
               'gap_registration','weather_registration','emotion_registration','mood_f4_registration']]
    with ZipFile(archive,'x',ZIP_DEFLATED) as z:
        for p,h in r['files'].items():
            data=(ROOT/p).read_bytes()
            if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Frozen source drift '+p)
            z.writestr(p,data)
        for p in extras:
            if p.is_file() and str(p.relative_to(ROOT)).replace('\\','/') not in r['files']:
                z.write(p,str(p.relative_to(ROOT)).replace('\\','/'))
    paths=sorted(p for p in (ROOT/'artifacts').glob('mood_f4_*') if p.is_file() and p.name!='mood_f4_delivery.json')
    supplemental=['scripts/mood_audit.py','scripts/mood_negative_audit.py','scripts/mood_continuity.py','scripts/mood_summary.py','scripts/package_mood_evidence.py',
                  'docs/MOOD_F4_REPORT.md','docs/MOOD_F4_OPERATIONS.md','docs/MOOD_F4_DEVELOPMENT_NOTES.md',
                  'README.md','docs/STATUS.md','HANDOFF.md']
    result=dict(files={str(p.relative_to(ROOT)).replace('\\','/'):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in paths},
                supplementary_sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in supplemental},
                note='Actual25 study SQLite saves remain local in ignored data/mood-f4-confirmation; audit inventories their hashes. No source world/reset/release change.')
    output=ROOT/'artifacts/mood_f4_delivery.json'
    if output.exists():raise ValueError('Refuse replacing evidence inventory')
    output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
