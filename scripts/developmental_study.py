"""Preregistered H1 native source-choice study. New worlds only, no model calls."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import developmental as dev, storage, teaching  # noqa: E402

SEEDS = [8101, 8111, 8123, 8147, 8161]
ARMS = ['learning', 'frozen', 'memory', 'authored']


def introduce(path, ident, material, mass, position):
    with dev.Lease(path):
        o = dev.own_observation(path, 'agent-1')
        return teaching.intervene(path, dict(schema_version=1, run_id=o['run_id'], branch_id=o['run_id'],
            intervention_id='add-' + ident, observation_version=o['observation_version'], kind='introduce_object',
            parameters=dict(entity_id=ident, x_m=position[0], y_m=position[1], material=material,
                            mass_kg=mass, energy_j=0)))


def identifier(rng):
    return 'x-' + f'{rng.getrandbits(60):015x}'


def train(path, seed, learn):
    rng = random.Random(seed + 100)
    records = []
    kinds = [('food', .05, [1, 3]), ('water', .05, [3, 3]),
             ('food', .05, [6, 3]), ('food', .0005, [2, 2]), None]
    schedule = list(range(5)) * 3
    rng.shuffle(schedule)
    for kind in schedule:
        if kinds[kind] is None:
            target = 'resource-4'
        else:
            material, mass, position = kinds[kind]
            target = identifier(rng)
            introduce(path, target, material, mass, position)
        prediction = dev.choose(path, 'agent-1', [target])
        result = dev.execute(path, 'agent-1', 'gather', [target], {'mass_kg': .001},
                             learn_food=learn, prediction=prediction)
        records.append(result)
    return records


def scenarios(path, seed):
    rng = random.Random(seed + 200)
    cases = []
    for i in range(12):
        scarcity = i % 4 == 3
        definitions = [('food', .05, 'near'), ('water', .05, 'near'), ('food', .05, 'far')]
        if i % 4 == 1:
            definitions[2] = ('food', .0004, 'near')
        if scarcity:
            definitions[0] = ('food', .0004, 'near')
        positions = [[1, 3], [2, 2], [3, 3]]
        rng.shuffle(positions)
        rng.shuffle(definitions)
        specs = []
        for j, (material, mass, reach) in enumerate(definitions):
            specs.append({'id': identifier(rng), 'material': material, 'mass': mass,
                          'position': [6 + .1 * (i % 2), 3] if reach == 'far' else positions[j]})
        cases.append({'case': i, 'feasible': not scarcity, 'specs': specs})
    return cases


def run_cell(directory, seed, arm):
    path = directory / f'{seed}-{arm}.sqlite'
    start = time.perf_counter()
    dev.initialize(path, seed=seed, population=1)
    training = train(path, seed, arm == 'learning')
    frozen = dev.private_state(path, 'agent-1', 'agent-1')
    cases = []
    for case in scenarios(path, seed):
        if time.perf_counter() - start > 120:
            raise TimeoutError('registered per-cell wall cap')
        for s in case['specs']:
            introduce(path, s['id'], s['material'], s['mass'], s['position'])
        ablation = None
        if arm == 'learning':
            backup = directory / f'{seed}-ablation-{case["case"]}.sqlite'
            storage.save(path, f'ablation-{case["case"]}', backup)
            same_head = storage.inspect(path)['state_hash'] == storage.inspect(backup)['state_hash']
            control = dev.choose(backup, 'agent-1', [s['id'] for s in case['specs']], 'frozen')
            ablation = {'same_native_head': same_head, 'frozen_choice': control,
                        'meaning': 'explicit same-state counterfactual; no new lifetime'}
        decision = dev.choose(path, 'agent-1', [s['id'] for s in case['specs']], arm)
        if ablation is not None:
            ablation['choice_changed'] = decision['target'] != ablation['frozen_choice']['target']
        if decision['target']:
            experience = dev.execute(path, 'agent-1', 'gather', [decision['target']], {'mass_kg': .001},
                                     prediction=decision, update_memory=False)
        else:
            experience = dev.execute(path, 'agent-1', 'rest', duration=1, prediction=decision,
                                     update_memory=False)
        cases.append(dict(case=case['case'], feasible=case['feasible'], decision=decision,
                          experience=experience, ablation=ablation))
    after = dev.private_state(path, 'agent-1', 'agent-1')
    assert after['associations'] == frozen['associations'] and after['objects'] == frozen['objects']
    snapshot = storage.inspect(path)
    with dev.closing(storage._connect(path, readonly=True)) as db:
        world, _, _, _ = storage._head(db)
        world.check_invariants()
    successes = sum(c['experience']['goal_success'] for c in cases if c['feasible'])
    feasible = sum(c['feasible'] for c in cases)
    report = dict(seed=seed, arm=arm, path=str(path), training=training, evaluation=cases,
        feasible=feasible, completed_goals=successes, completion=successes/feasible,
        scarcity_abstentions=sum(not c['feasible'] and not c['decision']['target'] for c in cases),
        rejection_reasons=dict(Counter(c['experience']['receipt']['error_code'] for c in cases
                                      if c['experience']['receipt']['status'] == 'rejected')),
        action_statuses=dict(Counter(c['experience']['receipt']['status'] for c in cases)),
        changed_learning_keys=len(frozen['associations']), learning_frozen_during_scoring=True,
        simulated_s=snapshot['simulated_time_s'], wall_s=time.perf_counter()-start,
        initial_state=training[0]['before'], final_snapshot=snapshot, private_state=after,
        replay=storage.replay(path), audit=dev.audit(path), model_calls=0,
        protective_fallbacks=0, curriculum_origin='authored_bounded_exploration')
    report['native_accounting_invariants'] = True
    (directory / f'{seed}-{arm}.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('seed','arm','completion','wall_s','simulated_s')}), flush=True)
    return report


def interval(successes, n):
    z = 1.96
    p = successes / n
    center = (p + z*z/(2*n))/(1+z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/(1+z*z/n)
    return [center-half, center+half]


def summarize(cells, seeds):
    rates = {a: sum(c['completion'] for c in cells if c['arm'] == a)/len(seeds) for a in ARMS}
    improvements = {a: sum(next(c['completion'] for c in cells if c['seed']==s and c['arm']=='learning') >
                            next(c['completion'] for c in cells if c['seed']==s and c['arm']==a)
                            for s in seeds) for a in ('frozen','memory')}
    invariants = all(c['replay']['replay_matches'] and c['learning_frozen_during_scoring'] and
                     c['model_calls']==0 and c['simulated_s']==27 and c['native_accounting_invariants'] for c in cells)
    ablation_changes = sum(bool(v.get('ablation') and v['ablation']['same_native_head'] and v['ablation']['choice_changed'])
                           for c in cells for v in c['evaluation'])
    complete = len(cells)==len(seeds)*4 and {(c['seed'],c['arm']) for c in cells}=={(s,a) for s in seeds for a in ARMS}
    gate = complete and invariants and ablation_changes > 0 and rates['learning']>=.8 and all(
        rates['learning']-rates[a]>=.2 and improvements[a]>=min(4,len(seeds)) for a in ('frozen','memory'))
    return {'rates':rates,'improved_seeds':improvements,'invariants':invariants,'complete':complete,
            'same_state_ablation_changed_choices':ablation_changes,
            'h1_gate':gate,'wilson_completion_intervals':{a:interval(sum(c['completed_goals'] for c in cells if c['arm']==a),
                sum(c['feasible'] for c in cells if c['arm']==a)) for a in ARMS},
            'interpretation':'Narrow native source-choice learning. Authored curriculum and sensory categories; no general intelligence claim.'}


def register(output):
    names=['underworld/developmental.py','scripts/developmental_study.py','config/developmental.toml',
           'docs/DEVELOPMENTAL_PROTOCOL.md','docs/DEVELOPMENTAL_CONTRACTS.md','tests/test_developmental.py']
    report={'mechanism':dev.MECHANISM,'development_seeds':[41],'confirmation_seeds':SEEDS,
            'files':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',choices=('development','confirmation'),required=True)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--registration',type=Path)
    args=p.parse_args()
    if args.split=='confirmation':
        if not args.registration:p.error('confirmation requires a prospective source registration')
        spec=json.loads(args.registration.read_text(encoding='utf-8'))
        assert spec['confirmation_seeds']==SEEDS
        assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in spec['files'].items())
    args.directory=args.directory.resolve();args.directory.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();cells=[];seeds=[41] if args.split=='development' else SEEDS
    for seed in seeds:
        for arm in ARMS:
            if time.perf_counter()-start>1800:raise TimeoutError('registered total wall cap')
            cells.append(run_cell(args.directory,seed,arm))
            args.output.write_text(json.dumps({'split':args.split,'cells':cells},indent=2)+'\n',encoding='utf-8')
    report={'split':args.split,'cells':cells,'summary':summarize(cells,seeds),'wall_s':time.perf_counter()-start}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary'],indent=2))


if __name__=='__main__':main()
