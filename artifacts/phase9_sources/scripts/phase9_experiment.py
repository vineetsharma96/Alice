"""Run the sealed Phase 9 study once; retain native worlds and all failures."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import random
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import storage
from underworld.config import load
from underworld.learning import PolicyStore, registration, features, request, execute, label_receipt, world_head, control, sha
from underworld.wire import dumps


def prepare(path, seed, kind, available):
    cfg = load(ROOT/'config/survival.toml')
    cfg['seed'] = seed
    cfg['world'].update(population=1, population_limit=1)
    cfg['agency']['policy'] = 'none'
    storage.create(path, cfg, scripted=False)
    if available:
        o = storage.observe(path, ['agent-1'])[0]
        r = execute(path, request(o, 'gather', available, 'inventory',
                                 ['resource-1' if kind == 'eat' else 'resource-2'], 1))
        if r['status'] != 'completed': raise ValueError(f'gather failed: {r}')
    return path


def clone(source, destination):
    # SQLite backup rather than file copy includes any committed journal state.
    with destination.open('xb'): pass
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)


def score(rows):
    tp = sum(r['label'] and r['prediction'] for r in rows)
    tn = sum(not r['label'] and not r['prediction'] for r in rows)
    fp = sum(not r['label'] and r['prediction'] for r in rows)
    fn = sum(r['label'] and not r['prediction'] for r in rows)
    return dict(balanced_accuracy=(tp/(tp+fn)+tn/(tn+fp))/2, tp=tp, tn=tn, fp=fp, fn=fn,
        native_rejections=sum(r['receipt']['status']=='rejected' for r in rows),
        abstentions=sum(not r['prediction'] for r in rows),
        consumed_kg=sum(r['requested_kg'] for r in rows if r['prediction'] and r['label']),
        rollout_ticks=sum(r['ticks'] for r in rows))


def bootstrap(differences):
    values = sorted(sum(sample)/len(sample) for sample in itertools.product(differences, repeat=len(differences)))
    return [values[int(.025*(len(values)-1))], values[int(.975*(len(values)-1))]]


def summarize(rows, seeds, arms, gate):
    per_seed = {}
    for seed in seeds:
        per_seed[str(seed)] = {stage:{arm:score([r for r in rows if r['seed']==seed and r['stage']==stage and r['arm']==arm])
                                    for arm in arms} for stage in ('A_after_A','B_after_B','A_after_B')}
    primary = {arm:[sum(per_seed[str(seed)][stage][arm]['balanced_accuracy'] for stage in ('A_after_A','B_after_B'))/2
                    for seed in seeds] for arm in arms}
    means = {arm:sum(v)/len(v) for arm,v in primary.items()}
    differences = {arm:[a-b for a,b in zip(primary['online'], primary[arm])] for arm in arms if arm != 'online'}
    intervals = {arm:bootstrap(v) for arm,v in differences.items()}
    strongest = max(('nearest_memory','bracket_memory'), key=means.get)
    retention = [per_seed[str(seed)]['A_after_A']['online']['balanced_accuracy']-
                 per_seed[str(seed)]['A_after_B']['online']['balanced_accuracy'] for seed in seeds]
    checks = dict(over_frozen=means['online']-means['frozen'] >= gate['over_frozen'],
        over_each_memory=all(means['online']-means[a] >= gate['over_each_memory'] for a in ('nearest_memory','bracket_memory')),
        positive_bootstrap_lower=intervals[strongest][0] > gate['bootstrap_lower_above'],
        retention_mean=sum(retention)/len(retention) <= gate['maximum_mean_retention_loss'],
        retention_each_seed=max(retention) <= gate['maximum_seed_retention_loss'], no_system_failures=True)
    return dict(per_seed=per_seed, primary_per_seed=primary, primary_means=means,
        paired_mean_differences={a:sum(v)/len(v) for a,v in differences.items()}, paired_bootstrap_95=intervals,
        strongest_memory=strongest, retention_loss_per_seed=retention, gate_checks=checks, advance=all(checks.values()))


def run(output):
    spec, seal = registration()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    manifest = dict(study=spec['study'], started_at_utc=datetime.now(timezone.utc).isoformat(), registration=seal,
        native_build_id=storage.load_native().build_id, orchestration_id=storage.orchestration_id(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                       ('underworld/learning.py','scripts/phase9_experiment.py','config/phase9_study.json','docs/PHASE9_PREREGISTRATION.md')},
        limits=spec['limits'], status='running', evidence_root=str(output.resolve()))
    def write(name, value): (output/name).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    write('manifest.json', manifest)
    rows = []; training = []; replayed = 0
    def guard():
        if time.monotonic()-started > spec['limits']['wall_seconds']: raise RuntimeError('wall budget exhausted')
        if sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) > spec['limits']['disk_bytes']:
            raise RuntimeError('disk budget exhausted')
    def check_replay(path):
        nonlocal replayed
        storage.replay(path); replayed += 1
    try:
        with (output/'evaluations.jsonl').open('x', encoding='utf-8') as stream, (output/'training.jsonl').open('x', encoding='utf-8') as trainstream:
            for seed in spec['seeds']:
                folder=output/f'seed-{seed}'; folder.mkdir()
                model=PolicyStore.create(folder/'policy.sqlite', seed); rng=random.Random(seed)
                def evaluate(stage, kind):
                    before=model.read(); state_hash=sha(before)
                    for i,(mass,fraction) in enumerate(itertools.product(spec['evaluation_requests_kg'][kind], spec['evaluation_available_fractions'])):
                        guard(); case=folder/f'{stage}-{i:02}'; case.mkdir()
                        base=prepare(case/'base.sqlite',seed,kind,round(mass*fraction,9))
                        world,_,_,head=world_head(base); o=world.observe_batch(['agent-1'])[0]; x=features(o,kind,mass)
                        # Predictions are committed to JSON before generating any probe label.
                        predictions={arm:control(arm,before,x) for arm in spec['arms']}
                        write(str(case.relative_to(output)/'predictions.json'),dict(policy_sha256=state_hash, before_head=head, x=x,predictions=predictions))
                        probe=case/'probe.sqlite'; clone(base,probe)
                        oracle=execute(probe,request(o,kind,mass,'probe')); label=label_receipt(oracle); check_replay(probe)
                        for arm in spec['arms']:
                            path=case/f'{arm}.sqlite'; clone(base,path)
                            if world_head(path)[3] != head: raise ValueError('paired initial head mismatch')
                            req=request(o,kind if predictions[arm] else 'rest',mass,'evaluation')
                            receipt=execute(path,req); check_replay(path)
                            if predictions[arm] and label_receipt(receipt)!=label: raise ValueError('probe/candidate mismatch')
                            if not predictions[arm] and receipt['status']!='completed': raise ValueError('abstention failure')
                            after=world_head(path)
                            if world.snapshot()['material_totals_ug'] != after[0].snapshot()['material_totals_ug']:
                                raise ValueError('conservation failure')
                            row=dict(seed=seed,stage=stage,case=i,arm=arm,kind=kind,requested_kg=mass,fraction=fraction,
                                x=x,prediction=predictions[arm],label=label,oracle=oracle,request=req,receipt=receipt,
                                before_head=head,after_head=after[3],policy_sha256=state_hash,ticks=10,path=str(path.relative_to(output)))
                            rows.append(row); stream.write(dumps(row)+'\n'); stream.flush()
                    if sha(model.read()) != state_hash: raise ValueError('evaluation changed policy or episodic memory')
                for block,kind in (('A','eat'),('B','drink')):
                    for epoch in range(spec['passes_per_block']):
                        schedule=list(itertools.product(spec['training_requests_kg'],spec['training_available_fractions'])); rng.shuffle(schedule)
                        for i,(mass,fraction) in enumerate(schedule):
                            guard(); rid=f'train-{block}-{epoch}-{i:02}'
                            path=prepare(folder/f'{rid}.sqlite',seed,kind,round(mass*fraction,9))
                            record=model.train(path,kind,mass,rid); check_replay(path)
                            row={k:v for k,v in record.items() if k!='before_checkpoint'} | dict(seed=seed,block=block,epoch=epoch)
                            training.append(row); trainstream.write(dumps(row)+'\n'); trainstream.flush()
                    evaluate('A_after_A' if block=='A' else 'B_after_B',kind)
                    print(f'seed {seed}: block {block}, {model.read()["version"]} verified training receipts', flush=True)
                evaluate('A_after_B','eat')
                write(str((folder/'final_policy.json').relative_to(output)),model.read())
        summary=summarize(rows,spec['seeds'],spec['arms'],spec['gate'])
        summary.update(training_trials=len(training), evaluation_rollouts=len(rows), native_replays_verified=replayed,
            training_mistakes=sum(r['before_weights']!=r['after_weights'] for r in training),
            failed_cases=[{k:r[k] for k in ('seed','stage','case','arm','x','label','prediction')} for r in rows if r['label']!=r['prediction']])
        guard(); write('summary.json',summary); manifest.update(status='completed',advance=summary['advance'])
    except BaseException as error:
        manifest.update(status='failed', advance=False, error=f'{type(error).__name__}: {error}',
                        completed_training_trials=len(training), completed_evaluation_rollouts=len(rows))
        raise
    finally:
        manifest.update(wall_time_s=time.monotonic()-started, finished_at_utc=datetime.now(timezone.utc).isoformat())
        manifest['retained_bytes']=sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
        write('manifest.json',manifest)
        files={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file() and p.name!='file_hashes.json'}
        write('file_hashes.json',files)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); result=run(args.output)
    print(json.dumps({k:result[k] for k in ('primary_means','paired_bootstrap_95','retention_loss_per_seed','gate_checks','advance')},indent=2))
