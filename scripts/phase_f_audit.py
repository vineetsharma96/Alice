"""Summarize retained F event evidence without rerunning or changing any world."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def main():
    registration=json.loads((ROOT/'artifacts/living_world_f_registration_final.json').read_text())
    matches={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in registration['files'].items()}
    results=json.loads((ROOT/'artifacts/living_world_f_confirmation_final.json').read_text())
    cases=[]
    for case in results['cases']:
        db=sqlite3.connect((ROOT/case['path']).resolve().as_uri()+'?mode=ro',uri=True)
        try:events=[json.loads(r[0]) for r in db.execute('SELECT payload FROM events ORDER BY seq')]
        finally:db.close()
        counts=Counter(e['type'] for e in events)
        failures=[e for e in events if e['type'] in ('action_failed','action_rejected')]
        linked=(case['teacher_test']['event_refs'][1]==case['book_claim']['origin_event_seq']
                and case['teacher_test']['lesson_source_id']=='operator:true-lesson'
                and case['student_test']['lesson_episode_id']==case['book_claim']['episode_id'])
        assert linked and counts['action_failed']==1 and counts['action_rejected']==0
        cases.append({'seed':case['seed'],'counts':dict(counts),'failures':failures,
                      'source_chain_matches':linked,'simulated_s':case['simulated_s'],'wall_s':case['wall_s'],
                      'resume_equal':case['resume_equal'],'isolated_third':case['isolated_control']['status']})
    protected=json.loads((ROOT/'artifacts/stabilization_registration.json').read_text())['phase9_files_sha256']
    phase9={name:hashlib.sha256((ROOT/Path(name.replace('\\','/'))).read_bytes()).hexdigest()==value for name,value in protected.items()}
    report={'passed':all(matches.values()) and all(phase9.values()),'registered_files':matches,'phase9_hashes':phase9,
            'cases':cases,'attribution':'authored lab execution; no model calls or deterministic fallback',
            'scope':'separate finite worlds, not one summed lifetime; no autonomous teaching claim'}
    (ROOT/'artifacts/living_world_f_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
