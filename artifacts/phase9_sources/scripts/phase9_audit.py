"""Independently check retained Phase 9 files and recompute its registered metrics."""
import argparse
import hashlib
import json
import itertools
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld.learning import PolicyStore, registration
from phase9_experiment import summarize


def audit(folder):
    spec,seal=registration()
    manifest=json.loads((folder/'manifest.json').read_text())
    if manifest['status']!='completed' or manifest['registration']!=seal: raise ValueError('incomplete or foreign study')
    for relative,expected in manifest['source_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected: raise ValueError(f'source drift: {relative}')
    hashes=json.loads((folder/'file_hashes.json').read_text())
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name!='file_hashes.json'}
    if actual!=set(hashes): raise ValueError('evidence file inventory changed')
    for relative,expected in hashes.items():
        if hashlib.sha256((folder/relative).read_bytes()).hexdigest()!=expected: raise ValueError(f'evidence changed: {relative}')
    rows=[json.loads(line) for line in (folder/'evaluations.jsonl').read_text().splitlines()]
    training=[json.loads(line) for line in (folder/'training.jsonl').read_text().splitlines()]
    if len(rows)!=840 or len(training)!=360: raise ValueError('incomplete registered counts')
    for seed in spec['seeds']:
        state=PolicyStore(folder/f'seed-{seed}/policy.sqlite').read()
        if state['version']!=72 or len(state['records'])!=72 or any(r['status']!='finished' for r in state['records']):
            raise ValueError('unresolved training')
        if state['seed']!=seed: raise ValueError('foreign policy seed')
        raw=[r for r in training if r['seed']==seed]
        rng=random.Random(seed); index=0
        for block,kind in (('A','eat'),('B','drink')):
            for epoch in range(spec['passes_per_block']):
                schedule=list(itertools.product(spec['training_requests_kg'],spec['training_available_fractions'])); rng.shuffle(schedule)
                for case,(mass,fraction) in enumerate(schedule):
                    r=raw[index]; journal=state['records'][index]; index+=1
                    expected={k:v for k,v in journal.items() if k!='before_checkpoint'} | dict(seed=seed,block=block,epoch=epoch)
                    if r!=expected or r['x']!=[round(mass*fraction,9),mass,1.] or r['request']['action_type']!=kind:
                        raise ValueError('registered training schedule or published trace mismatch')
                    if r['request']['request_id']!=f'train-{block}-{epoch}-{case:02}': raise ValueError('training identity mismatch')
    recalculated=summarize(rows,spec['seeds'],spec['arms'],spec['gate'])
    summary=json.loads((folder/'summary.json').read_text())
    for key,value in recalculated.items():
        if summary[key]!=value: raise ValueError(f'metric disagreement: {key}')
    for seed in spec['seeds']:
        for stage in ('A_after_A','B_after_B','A_after_B'):
            for case in range(14):
                group=[r for r in rows if r['seed']==seed and r['stage']==stage and r['case']==case]
                if len(group)!=4 or len({r['before_head'] for r in group})!=1 or len({r['policy_sha256'] for r in group})!=1:
                    raise ValueError('unpaired case')
                if len({r['label'] for r in group})!=1: raise ValueError('inconsistent native probe label')
                kind='drink' if stage=='B_after_B' else 'eat'
                mass,fraction=list(itertools.product(spec['evaluation_requests_kg'][kind],spec['evaluation_available_fractions']))[case]
                if {r['arm'] for r in group}!=set(spec['arms']) or any(r['kind']!=kind or r['requested_kg']!=mass or
                        r['fraction']!=fraction or r['x']!=[round(mass*fraction,9),mass,1.] or r['ticks']!=10 for r in group):
                    raise ValueError('registered evaluation grid mismatch')
                pred=json.loads((folder/f'seed-{seed}/{stage}-{case:02}/predictions.json').read_text())
                if any(pred['predictions'][r['arm']]!=r['prediction'] or pred['before_head']!=r['before_head'] for r in group):
                    raise ValueError('prediction commitment mismatch')
    return dict(verified_files=len(hashes), verified_source_files=len(manifest['source_sha256']), training_trials=len(training),
        evaluation_rollouts=len(rows), paired_evaluation_cases=210, finished_policy_journals=5,
        recomputed_metrics_match=True, evidence_sha256=hashlib.sha256((folder/'file_hashes.json').read_bytes()).hexdigest(),
        advance=summary['advance'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--study',required=True,type=Path)
    args=p.parse_args(); print(json.dumps(audit(args.study),indent=2))
