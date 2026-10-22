"""Package exact frozen sources and evidence inventory without changing studies."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]


def main():
    registration=json.loads((ROOT/'artifacts/emotion_registration.json').read_text(encoding='utf8'))
    source_path=ROOT/'artifacts/emotion_frozen_sources.zip'
    if source_path.exists():raise ValueError('Refuse replacing source archive')
    with ZipFile(source_path,'x',ZIP_DEFLATED) as archive:
        for p,expected in registration['files'].items():
            content=(ROOT/p).read_bytes()
            if hashlib.sha256(content).hexdigest()!=expected:raise ValueError('Source drift '+p)
            archive.writestr(p,content)
        for p in sorted((ROOT/'core').glob('*')):
            if p.is_file():archive.write(p,str(p.relative_to(ROOT)))
        archive.write(ROOT/'CMakeLists.txt','CMakeLists.txt')
    paths=[source_path]+[p for p in (ROOT/'artifacts').glob('emotion_*') if p.is_file() and p.name!='emotion_delivery.json']
    supplemental=['scripts/emotion_audit.py','scripts/emotion_continuity.py','scripts/emotion_summary.py',
                  'scripts/package_emotion_evidence.py','docs/EMOTION_REPORT.md','docs/EMOTION_OPERATIONS.md',
                  'docs/EMOTION_DEVELOPMENT_NOTES.md','HANDOFF.md','README.md','docs/STATUS.md']
    result=dict(files={str(p.relative_to(ROOT)).replace('\\','/'):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(paths)},
                supplementary_sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in supplemental},
                note='Native SQLite saves remain local in ignored data/emotion-confirmation; replay audit records their exact hashes. No save reset, migration or release.')
    output=ROOT/'artifacts/emotion_delivery.json'
    if output.exists():raise ValueError('Refuse replacing delivery inventory')
    output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
