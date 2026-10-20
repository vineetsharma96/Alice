"""Publish a local report from audited study evidence, without rerunning trials."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from phase9_audit import audit
from phase9_experiment import score


def publish(folder):
    checked=audit(folder)
    summary=json.loads((folder/'summary.json').read_text())
    manifest=json.loads((folder/'manifest.json').read_text())
    rows=[json.loads(line) for line in (folder/'evaluations.jsonl').read_text().splitlines()]
    training=[json.loads(line) for line in (folder/'training.jsonl').read_text().splitlines()]
    for source,target in [('manifest.json','study_manifest.json'),('summary.json','summary.json'),
                          ('training.jsonl','training.jsonl'),('evaluations.jsonl','evaluations.jsonl'),('file_hashes.json','file_hashes.json')]:
        shutil.copyfile(folder/source,ROOT/'artifacts'/f'phase9_{target}')
    (ROOT/'artifacts/phase9_audit.json').write_text(json.dumps(checked,indent=2)+'\n')
    means=summary['primary_means']
    table=['| Arm | Primary balanced accuracy | Rejections | Abstentions | Missed feasible | Consumed kg |',
           '|---|---:|---:|---:|---:|---:|']
    for arm in ('frozen','nearest_memory','bracket_memory','online'):
        s=score([r for r in rows if r['arm']==arm])
        table.append(f"| {arm} | {means[arm]:.2%} | {s['native_rejections']} | {s['abstentions']} | {s['fn']} | {s['consumed_kg']:.6f} |")
    seedtable=['| Seed | Frozen | Nearest memory | Bracket memory | Online | A retention loss |',
               '|---|---:|---:|---:|---:|---:|']
    for i,seed in enumerate((11,22,33,44,55)):
        values=[summary['primary_per_seed'][a][i] for a in ('frozen','nearest_memory','bracket_memory','online')]
        seedtable.append('| '+str(seed)+' | '+' | '.join(f'{v:.2%}' for v in values)+f" | {summary['retention_loss_per_seed'][i]*100:+.2f} pp |")
    differences=['| Comparator | Mean online minus control | Paired bootstrap 95% interval |','|---|---:|---|']
    for arm,diff in summary['paired_mean_differences'].items():
        lo,hi=summary['paired_bootstrap_95'][arm]
        differences.append(f'| {arm} | {diff*100:+.2f} pp | [{lo*100:+.2f}, {hi*100:+.2f}] pp |')
    checks='\n'.join(f'- {name}: **{"pass" if passed else "fail"}**.' for name,passed in summary['gate_checks'].items())
    failures=Counter((r['arm'],r['label'],r['prediction']) for r in rows if r['label']!=r['prediction'])
    failuretext='\n'.join(f'- {arm}: {count} '+('false positives (infeasible action attempted).' if not label else 'false negatives (feasible action missed).')
                          for (arm,label,pred),count in sorted(failures.items()))
    examples=[r for r in rows if r['arm']=='online' and r['label']!=r['prediction']][:8]
    exampletext='\n'.join(f"- Seed {r['seed']}, {r['stage']}, {r['kind']}: inventory {r['x'][0]:.6f} kg, request {r['requested_kg']:.6f} kg; predicted {r['prediction']}, native feasible {r['label']}." for r in examples)
    positive=sum(r['label'] for r in training)
    verdict='passed' if summary['advance'] else 'failed'
    action='The registered gate permits considering a separately reviewed integration.' if summary['advance'] else 'The learner remains outside autonomous agents. No advancement or deployment is authorized by these results.'
    text=f'''# Phase 9 experiment report — 2026-10-20

The registered advancement gate **{verdict}**. {action} The bounded five-seed experiment completed; a completed research experiment is distinct from evidence that its mechanism is useful.

## Hypothesis and preregistration

Test whether a non-neural three-weight online policy can learn consumption feasibility from its own native action receipts and outperform frozen and memory-only controls on fixed unseen quantities, while retaining task A after learning task B. The [preregistration](PHASE9_PREREGISTRATION.md) and [sealed configuration](../config/phase9_study.json) were written before the first study trial. No pilot, hyperparameter amendment or outcome-driven rerun occurred. Unit fixtures tested implementation separately and were never training data. The first native source-verification unit test exposed a missing run-ID argument during checkpoint restoration; it was fixed before the study.

The seal artifact's `registered_at_utc` uses the pre-work clock reading 00:08:58 UTC. Its observed filesystem creation/write time was 00:12:21 UTC, before the study began at {manifest['started_at_utc']}; the earlier field should not be interpreted as the exact sealing instant. The study finished at {manifest['finished_at_utc']}.

## Protocol and controls

Five seeds (11,22,33,44,55) shuffle training order independently. Each trains 36 eat trials, evaluates A, trains 36 drink trials with the same weights, evaluates B, then reevaluates A. Features are own available kg, proposed kg and bias. A normalized perceptron updates on mistakes only, learning rate 0.25, weights clipped to [-8,8]. Training deliberately attempts every curriculum candidate to obtain native feedback; evaluation selects attempt or rest using each arm's prediction, with all training state frozen. This is supervised online action selection, not reinforcement learning or neural optimization.

Frozen starts and stays at zero weights (always attempt). Nearest-memory uses one nearest native training receipt. Bracket-memory is an explicitly stronger, domain-informed authored baseline that derives an inventory-minus-request threshold from receipt margins. It has the same records and no trained weights. All controls and the learner use identical training feedback. No prompts, books, pretrained models, inherited parameters, private cross-agent data or viewer diagnostics influence predictions.

The 14-case fixed evaluation per stage contains unseen requested quantities and availability fractions 0,0.9,0.99,1,1.01,1.1,2. Predictions are persisted before the native probe executes. Each probe and the four arms start from an exact paired saved head; evaluation labels update neither parameters nor memory. Every rollout advances 10 ticks at dt=0.2 seconds, including rejections and rest. Native gathering creates inventory; no direct body edits are used. Each fresh episode has one actor, fixed 16 kg food/64 kg water, no regeneration, and at most three simulated seconds. These are short episodes with persistent parameters, not a long continuous world horizon.

## Results

Primary accuracy averages A-after-A and B-after-B equally, then the five seeds. Remaining columns aggregate all three evaluation stages: 210 rollouts per arm. A false negative is a missed feasible action, so abstaining cannot manufacture a win.

{chr(10).join(table)}

Per-seed primary balanced accuracy and online retention loss (A-after-A minus A-after-B; positive means forgetting):

{chr(10).join(seedtable)}

{chr(10).join(differences)}

Intervals enumerate all 5^5 paired bootstrap resamples of training-order seeds. They are descriptive and conditional on this one authored task and fixed evaluation set. They do not estimate broad task generalization or provide strong population evidence. Strongest memory control: `{summary['strongest_memory']}`.

## Gate and failure cases

{checks}

The locked gate requires >=10 percentage points over frozen, >=5 points over EACH memory control, a strictly positive bootstrap lower bound against the strongest memory control, and <=5 points of A retention loss both on average and for every seed, with no system/integrity failures. The gate was not weakened after results.

{failuretext}

First retained online errors (the summary contains every error, including boundary/equality cases):

{exampletext or 'No online classification errors occurred.'}

Task B shares the same feasibility law as task A. Its retention test probes only narrow interference under a second shuffled training block on the same quantity grid; it does not establish general resistance to catastrophic forgetting. Learning depends on curriculum order and a tiny linear representation. A useful next research change would require a new explicit study and preregistration, not tuning this study until it passes.

## Native provenance and costs

There were **{len(training)} verified training trials** ({positive} completed candidates, {len(training)-positive} native inventory rejections), **{summary['training_mistakes']} parameter-changing mistakes**, **840 evaluation rollouts**, and **210 native counterfactual probes**. All **{summary['native_replays_verified']}** training/probe/rollout databases passed native replay during the study; evaluation rollouts also checked material conservation. Five final journals each contain exactly 72 finished records. The independent audit verified {checked['verified_files']} retained evidence files, paired states/prediction commitments and recomputed metrics. Policy-state hashes were unchanged across each evaluation stage.

Trial/evaluation wall time: **{manifest['wall_time_s']:.3f} seconds** against the registered 900-second limit, excluding final evidence hashing and separate audit/report publication. Retained evidence before final manifest/hash inventory: **{manifest['retained_bytes']/2**20:.2f} MiB** against 512 MiB. Disk quota is checked between bounded cases; this research script is not an OS memory or network sandbox. [A process-memory sample](../artifacts/phase9_resources.json) records only the actual study Python process's observed peak during the run, excluding browser/GPU/other-process totals; it is not a final whole-machine peak. No inference server, neural dependency, C++ rebuild, database migration or runtime-policy integration was added. Source IDs are pinned in the [study manifest](../artifacts/phase9_study_manifest.json); native UW6/DB7 and the durable orchestration identity remain unchanged.

Native world commits and policy commits are separate. Reservations capture pre-action evidence; finishing verifies the committed request and reproduces the native terminal head before applying feedback exactly once. A crash before submission leaves an unresolved reservation and never replays a physical action. A partial action is not completion. Checksum/update-chain tests and source checks detect accidental corruption or foreign receipts, not an adversary who can rewrite every local artifact. Full pre-action checkpoints are privileged audit metadata; prediction functions use only weights and own receipt features/labels.

## Published local artifacts and verification

- [Study manifest](../artifacts/phase9_study_manifest.json), [summary and all failures](../artifacts/phase9_summary.json), [audit](../artifacts/phase9_audit.json), and [evidence hashes](../artifacts/phase9_file_hashes.json).
- [Training receipts and weight changes](../artifacts/phase9_training.jsonl) and [evaluation requests/receipts](../artifacts/phase9_evaluations.jsonl).
- Native SQLite worlds and final parameters: `{str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else folder}`. These generated data files are ignored by Git and retained locally; the compact reports/traces above are publishable workspace artifacts.
- Twelve new learning tests cover native feedback, persistence/restart, exactly-once reconciliation, incomplete actions, foreign/forged sources, tampering, frozen controls, input boundaries, equality and conservation.
- An initial full verification attempt timed out at 120 seconds while competing with this study; its four native checks passed. That attempt is preserved in [phase9_verification_attempt1.json](../artifacts/phase9_verification_attempt1.json). The final [full verification record](../artifacts/phase9_checks.json) records the separate rerun and its exact outcome.

Reproduce only into a new directory with `python scripts/phase9_experiment.py --output data/phase9-replication`. Audit retained results with `python scripts/phase9_audit.py --study data/phase9-study-20261020`. Neither inspection nor report publication advances the running Phase 8 preview.

No claim of sentience, biological reproduction, generalized endogenous improvement or guaranteed civilization emergence follows. Generations/inheritance, the separate artificial-life origins track, longer world horizons, speech and true 3D mechanics remain deferred. R7/R8/R10/R11 context and boundaries are recorded in [REFERENCES.md](REFERENCES.md).
'''
    (ROOT/'docs/PHASE9_REPORT.md').write_text(text,encoding='utf-8')
    print(json.dumps(checked,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--study',required=True,type=Path)
    publish(parser.parse_args().study.resolve())
