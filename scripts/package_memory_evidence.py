"""Package exact registered F5 source and an inventory of retained evidence."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def main():
    registration=json.loads((ROOT/'artifacts/memory_f5_registration.json').read_text(encoding='utf8'))
    output=ROOT/'artifacts/memory_f5_delivery.json'
    if output.exists():raise ValueError('Refuse replacing evidence inventory')
    with ZipFile(ROOT/'artifacts/memory_f5_frozen_sources.zip','x',ZIP_DEFLATED) as z:
        for p,h in registration['files'].items():
            data=(ROOT/p).read_bytes()
            if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Frozen source drift '+p)
            z.writestr(p,data)
        extra=[ROOT/'CMakeLists.txt']+list((ROOT/'core').glob('*'))
        extra+=list((ROOT/'artifacts').glob('*registration*.json'))
        for p in extra:
            name=str(p.relative_to(ROOT)).replace('\\','/')
            if p.is_file() and name not in registration['files']:z.write(p,name)
    artifacts=sorted(p for p in (ROOT/'artifacts').glob('memory_f5_*') if p.is_file())
    supplemental=['scripts/memory_audit.py','scripts/memory_audit_summary.py','scripts/memory_negative_audit.py','scripts/memory_continuity.py','scripts/memory_continuity_proof.py','scripts/memory_summary.py','scripts/package_memory_evidence.py',
                  'scripts/verify_memory_viewer.mjs','docs/MEMORY_F5_REPORT.md','docs/MEMORY_F5_OPERATIONS.md',
                  'docs/MEMORY_F5_DEVELOPMENT_NOTES.md','HANDOFF.md','HANDOFF_PRE_F5_ARCHIVE.md','README.md','docs/STATUS.md']
    result=dict(files={str(p.relative_to(ROOT)).replace('\\','/'):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in artifacts},
                supplementary_sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in supplemental},
                note='Actual native SQLite saves remain local under ignored data/; audit hashes identify them. Historical failures and development copies are preserved. No release/reset.')
    output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
