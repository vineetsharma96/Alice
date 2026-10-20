"""Build the stabilization handoff from retained evidence; never rerun policies."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import stabilization as stable
from stabilization_common import read,write


def main():
    def load(name):return json.loads((ROOT/'artifacts'/name).read_text(encoding='utf-8-sig'))
    evaluation=load('stabilization_heldout_v3.json');continuity=load('stabilization_continuity.json')
    verification=load('stabilization_checks.json');baseline=load('stabilization_baseline.json')
    registration=load('stabilization_registration.json');freeze=load('stabilization_heldout_v3_freeze.json')
    if len(evaluation['cases'])!=60:raise ValueError('incomplete amended evaluation')
    if stable.source_id()!=freeze['controller_source_id']:raise ValueError('controller changed after held-out freeze')
    preservation={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==value for p,value in registration['phase9_files_sha256'].items()}
    if not all(preservation.values()):raise ValueError('protected Phase 9 file changed')
    summary={}
    table=['| Arm | Feasible goals completed | Missed feasible | Native submission rejections | Completed actions | Calls / provider failures | Median case wall s |',
           '|---|---:|---:|---:|---:|---|---:|']
    for arm in ('utility','legacy_model','stable_authored','stable_model'):
        cases=[c for c in evaluation['cases'] if c['arm']==arm]
        feasible=sum(sum(c['feasible_goals'].values()) for c in cases)
        achieved=sum(sum(c['feasible_goals'][k] and c['achieved_goals'][k] for k in c['feasible_goals']) for c in cases)
        completed=Counter();accepted=Counter();errors=Counter();latencies=[];failures=0;valid_json=0;compiled=0;calls=0
        origins=Counter();model_completed=0;fallback_completed=0;authored_steps=0
        for c in cases:
            completed.update(c['completed_actions']);accepted.update(c['accepted_requests']);errors.update(c['native_error_reasons'])
            if arm=='legacy_model':
                for q in c['cognition_calls']:
                    calls+=1;failures+=q['status']=='fallback';latencies.append(q['latency_s'])
                    try:json.loads(q['raw']);valid_json+=1
                    except (ValueError,TypeError):pass
                    compiled+=q['status']=='planned'
            else:
                for q in c.get('inference_results',[]):
                    calls+=1;valid_json+=q['valid_json'];compiled+=q['compiled'];latencies.append(q['latency_s'])
                    failures+=bool(q['error'] and q['error']!='need_override_of_non_survival_choice')
                for e in c.get('controller_events',[]):
                    if e['kind']=='goal_selected':origins[e['data']['origin']]+=1
                    if e['kind']=='goal_completed' and e['data']['kind'] in ('eat','drink') and e['data']['reason']=='native_ingested_reservoir_delta':
                        model_completed+=e['data']['origin']=='model_selection'
                        fallback_completed+=e['data']['origin']=='deterministic_fallback'
                authored_steps+=c.get('controller',{}).get('authored_steps',0)
        rejection_count=sum(1 for c in cases for t in c['traces'] if t['submitted']['status']=='rejected')
        goal_times={material:[min(int(t['terminal_receipt']['completed_tick'])-int(c['initial_observation']['tick'])
            for t in c['traces'] if t['request']['action_type']==action and t['terminal_receipt'] and t['terminal_receipt']['status']=='completed')
            for c in cases if any(t['request']['action_type']==action and t['terminal_receipt'] and t['terminal_receipt']['status']=='completed' for t in c['traces'])]
            for material,action in (('food','eat'),('water','drink'))}
        summary[arm]=dict(feasible_goals=feasible,completed_feasible_goals=achieved,missed=feasible-achieved,
            native_submission_rejections=rejection_count,preventable_rejections=sum(len(c['preventable_rejections']) for c in cases),
            completion_time_failures=sum(len(c['completion_time_failures']) for c in cases),accepted_requests=dict(accepted),
            completed_actions=dict(completed),native_error_reasons=dict(errors),inference_calls=calls,provider_failures=failures,
            valid_json=valid_json,compiled_original_model_outputs=compiled,model_latencies_s=latencies,
            model_latency_median_s=statistics.median(latencies) if latencies else None,
            goal_origins=dict(origins),model_selected_consumption_completions=model_completed,fallback_selected_consumption_completions=fallback_completed,
            authored_execution_steps=authored_steps,median_case_wall_s=statistics.median(c['wall_s'] for c in cases),
            consumption_completion_simulated_s=goal_times,
            median_consumption_completion_simulated_s={k:statistics.median(v) if v else None for k,v in goal_times.items()},
            alive=sum(c['alive'] for c in cases),needs={k:dict(maximum=max(c['needs'][k]['maximum'] for c in cases),
                seconds_above_085=sum(c['needs'][k]['seconds_above_085'] for c in cases)) for k in ('hunger','thirst','fatigue')})
        s=summary[arm]
        table.append(f"| {arm} | {achieved}/{feasible} | {feasible-achieved} | {rejection_count} | {sum(completed.values())} | {calls} / {failures} | {s['median_case_wall_s']:.3f} |")
    write(ROOT/'artifacts/stabilization_summary.json',dict(arms=summary,heldout_checks=evaluation['checks'],continuity_checks=continuity['checks'],phase9_preserved=preservation))
    horizon=['| Arm | Actual continuous simulated s | Primary wall s | Alive | Fresh-process and recorded-request parity |',
             '|---|---:|---:|---|---|']
    for c in continuity['cases']:
        parity=c['recorded_command_parity']
        horizon.append(f"| {c['arm']} | {c['final']['tick']} | {c['primary_wall_s']:.3f} | {c['final']['own']['alive']} | {bool(parity and parity['native_hash_matches'] and parity['own_memory_matches'])} |")
    checks='\n'.join(f'- {k}: **{"pass" if v else "fail"}**.' for k,v in evaluation['checks'].items())
    tests=next(c for c in verification['checks'] if 'unittest' in c['command'])
    testline=next((line.strip() for line in tests['stderr'].splitlines() if line.startswith('Ran ')),'See verification output')
    passed=all(c['returncode']==0 for c in verification['checks'])
    sm=summary['stable_model'];lm=summary['legacy_model']
    result='passed' if evaluation['passed'] else 'failed'
    text=f'''# Underworld Lab stabilization report

The **fresh-cohort everyday-action evaluation {result}** its registered thresholds after disclosed development and evaluation failures. This is an authored execution improvement. Phase 9's failed learner remains unchanged and outside live policies. Results below apply to the selected inhabitant/scenarios; they do not establish general autonomous competence or all-population reliability.

## Baseline reproduced before implementation

The unchanged utility and local-model paths were each run for 20 native seconds with initially nonurgent needs and again after 160 seconds of actual body aging. Full inputs, raw outputs, compile status, submissions, receipts, needs and latency are retained in [stabilization_baseline.json](../artifacts/stabilization_baseline.json).

- Nonurgent model call 1 had empty carried inventory in its permitted context, generated/compiled an eat intent, then received native INSUFFICIENT_RESOURCE. Observation and submission were at the same native tick, with no earlier inventory-changing action: this case is not explained by stale state or execution order. The inventory observation was present. The old intent vocabulary cannot express gather/move prerequisites, and the compiler maps eat directly to a fixed consumption request.
- Nonurgent model call 2 exceeded its inference deadline (20.251 s end-to-end), used the explicit authored provider fallback, and completed speech. A completed speech action is not a completed meal or survival goal.
- Both aged-needs model outputs compiled, but the legacy scheduler preempted their pending plans because hunger/thirst were urgent. No native request was submitted. With utility disabled in the model-only arm, nothing supplied the missing execution. This is a scheduler/goal-arbitration failure, not a native rejection.
- Utility completed native gathering/consumption actions in the aged case. Those successes are deterministic utility behavior, not model planning.

These explanations apply to these traced cases. They do not retroactively assign one cause to every earlier Phase 7 rejection. Valid JSON, original-model compilation, submission acceptance, terminal action completion and goal achievement remain separate in the artifacts.

## Implementation

`underworld.stabilization` is an opt-in controller with explicit persistent goals: locate permitted supply → approach → gather → consume. It reobserves before every request, checks bounded alternative approach directions when one is occupied, waits for terminal native receipts, bounds search/retries/deadlines and records scarcity/blocked outcomes. Eating/drinking success requires a real ingested-mass delta and identifies whether the executor or an external action caused consumption.

The model selects an intent/goal; all prerequisite execution is authored. Deterministic need selection after the inference budget/interval and safety overrides of non-survival choices are recorded as fallback. The new context adds only geometry, reach and resource quantities already visible to the inhabitant. Private memory retrieval remains actor-specific. The native validator, legacy utility/model compiler and durable runtime sources are unchanged.

An explicit scheduler handoff disables old automatic utility/cognition dispatch and supersedes pending legacy plans while preserving physical state, pending native actions, inventories, needs, identities, episodes and prior journals. Controller state/audit tables are checksummed and source-pinned. Reservations commit before native ticks; recovery reconciles committed request IDs instead of resubmitting them. An unsubmitted reservation is discarded and replanned. These are separate transactions, not an atomic cross-database promise.

## Protocol, development and fixture amendment

The [protocol](STABILIZATION_PROTOCOL.md) was sealed before modified-policy measurements. Development used seed 101. The original cohort was 202,303,404; the final fresh cohort was 808,909,1001 following [amendment 2](STABILIZATION_AMENDMENT_2.md). Both used the same five scenarios, four arms and thresholds. Each evaluation lasted 90 continuous simulated seconds after native fixture aging/setup. Model arms received one inference attempt at the start, with logical time paused; the stabilized arm then used declared authored execution and deterministic fallback as needed. This budgeted model-only baseline is separate from a utility-plus-model system in which utility can mask model failures.

The first partial held-out attempt was stopped after a fixture bug was found. Actor 2's seeded random position did not guarantee reach to food; its competitor gather was rejected and the supposed depleted food remained available. Its 17 completed cases, native databases, evaluator source, freeze and [failure record](../artifacts/stabilization_heldout_attempt1_failure.json) are retained and excluded from the final comparison. Successful-looking results from that invalid depletion setup are not counted as depletion evidence.

[Amendment 1](STABILIZATION_AMENDMENT_1.md) moved the competitor natively to a declared reachable position, retained all setup time/costs, and added assertions for its completed receipt and actual empty source. Three independent native fixture validations and a repeated development run passed before the second comparison. The v1 controller remained frozen for that comparison.

The second, valid-fixture comparison then **failed**: model-selected unavailable food led to a missed feasible water goal. At (1,1), the single radial approach point for water was blocked by the visible peer at (2,1). The controller kept reporting no_perceived_route without trying another approach. This was a navigation defect, not a timeout, missing observation or native rejection. Its partial [results](../artifacts/stabilization_heldout_v2_failed.json), [failure record](../artifacts/stabilization_heldout_v2_failure.json), source and databases remain preserved.

[Amendment 2](STABILIZATION_AMENDMENT_2.md) added development regressions and controller version 2's bounded approach candidates using existing perceived-geometry helpers. The unchanged utility baseline already uses approach candidates. The repaired source was frozen before the final **new cohort** (808,909,1001), with no threshold, quantity or inference-budget relaxation. Earlier exposed seeds are excluded from the final aggregate. This is a fresh-cohort evaluation after an outcome-prompted disclosed repair, not a claim that the original hold-out stayed untouched. Failed attempts are not combined into favorable totals.

## Fresh-cohort comparison

{chr(10).join(table)}

Each arm has 24 feasible food/water goals across 15 cases. Unavailable/depleted food is excluded only from the feasible-food denominator; hunger, missing consumption, waits and all errors remain recorded. Native competitor receipts confirm real depletion in every corrected depleted case. Necessary scarcity is not a failed feasible goal. Completion-time physical failures are reported separately from fresh submission errors; they are not all assumed unavoidable.

Case wall time includes inference, controller/persistence work and, for interrupted cases, a second uninterrupted continuation used for parity. Main-process CPU fields exclude model-server/child CPU. Exact per-case timings, accepted/completed action kinds, rejection reasons, needs and source attribution are in [the fresh-cohort raw comparison](../artifacts/stabilization_heldout_v3.json) and [summary](../artifacts/stabilization_summary.json). These host-specific timings are not a universal speed claim.

The summary also derives consumption-completion latency in simulated seconds from native terminal receipts, separately for food/water. Those latencies are conditional on completion; missing goals stay in the missed-feasible denominator and are not assigned an artificial zero latency. Need maxima and seconds above 0.85 remain reported for each arm, including scarcity cases.

The stabilized model arm made {sm['inference_calls']} inference attempts: {sm['valid_json']} raw valid-JSON outputs and {sm['compiled_original_model_outputs']} original outputs that compiled; {sm['provider_failures']} provider failures. Its median end-to-end inference latency was {sm['model_latency_median_s']:.3f} s. The legacy model arm had {lm['compiled_original_model_outputs']} original outputs compile across {lm['inference_calls']} attempts; a compiled plan still does not imply submission or completion.

The stabilized model arm recorded {sm['model_selected_consumption_completions']} native consumption-goal completions whose goal was model-selected and {sm['fallback_selected_consumption_completions']} whose goal was fallback-selected. Its {sm['authored_execution_steps']} execution steps were authored. Model selection of eat does not establish that the model planned the approach/gather sequence. Matching utility here does not establish a model advantage over deterministic survival.

### Locked checks

{checks}

## Continuous worlds and save/resume

{chr(10).join(horizon)}

Each stabilized arm used one continuous one-inhabitant world with 2 kg initial food, 4 kg water and regeneration zero. Cumulative targets were 30,120,600,1200 seconds with a 240-second primary wall allowance per arm. A backup at 120 seconds was resumed by fresh Python processes. Each child verified exact incoming native/body/memory/controller state; call budgets and goal/navigation schedules were not reset. Actual cutoffs, if any, remain in [continuity evidence](../artifacts/stabilization_continuity.json).

Conservation and boundary-source checks compare against the original world. The uninterrupted native counterpart uses the same recorded commands, without regenerating inference; its final physical hash and own-memory view are compared to the resumed world. That is native/mental recorded-command parity, not a replay of every controller decision. Separate regression tests compare uninterrupted versus resumed full controller/scheduler state mid-action. Primary wall time excludes the additional recorded-command parity pass, whose cost is retained separately. Independent evaluation cases and the two continuous arms are not one summed lifelong horizon.

## Verification and preserved research

Full verification success: **{passed}**. {testline}. All native CTest results, exact commands, output and wall times are retained in [stabilization_checks.json](../artifacts/stabilization_checks.json). New regression cases cover prerequisite ordering, current inventory, depleted supply, scarcity, native conservation, handoff, disabled legacy scheduling, private input, audit corruption, inference fallback budgets, external interruption/consumption attribution, mid-action save/resume and both sides of the reservation/native-commit gap.

Protected Phase 9 files match their pre-milestone hashes: **{all(preservation.values())}**. The independent original study audit is retained in [stabilization_phase9_preservation.json](../artifacts/stabilization_phase9_preservation.json). Its failed comparison and retention gate is unchanged. The new executor has no learner import and introduces no neural training, reproduction, speech or true 3D mechanics.

## Remaining limitations and operation

- This is a bounded authored survival-goal executor, not a general planner. Capacity-blocked cargo rearrangement, arbitrary complex tasks, broad need combinations and all crowd layouts remain outside the demonstrated reliability claim. The primary evaluation controls actor 1 with a second fixture/competitor actor; continuous evidence is one active inhabitant per world.
- Repeated finite-resource operation can still exhaust supply. Scarcity search/cooldown can delay another need. No long-term sustainability, full-day stability, water-scarcity generalization or unrestricted goal arbitration is established.
- The model is still a small pretrained prior. The context and execution architecture changed together; this comparison does not isolate a prompt-only effect or demonstrate learned multi-step planning. Fallback dependence is part of the result.
- The opt-in runner is a bounded host-side development controller, not a newly verified AppContainer service. The old viewer/supervisor does not drive it automatically; use a read-only viewer and the new run command. No broad security, power-loss or cross-platform guarantee is added.
- Native state hashes exclude the additional control tables. Controller checksums/source identity and native replay are separate checks. Local checksums do not authenticate evidence against a hostile writer who can rewrite everything. Journals/native request limits remain finite; no controller-history compaction or source migration is provided.
- Small fixed scenario sets and the disclosed repair/evaluation iterations limit generalization. Fresh seeds do not establish broad task diversity. A further mechanism or changed acceptance criterion needs a new explicit evaluation, not a silent weakening of this one.

Runnable commands and existing-world backup/handoff are in [STABILIZATION_OPERATIONS.md](STABILIZATION_OPERATIONS.md). The original brief and Phase 9 study remain preserved. No consciousness, general intelligence or civilization-emergence claim follows from these results.
'''
    (ROOT/'docs/STABILIZATION_REPORT.md').write_text(text,encoding='utf-8')
    overall=passed and evaluation['passed'] and all(continuity['checks'][k] for k in ('survival','conservation','fresh_process_continuity','replay'))
    state='complete within measured scope' if overall else 'checks incomplete or failed'
    status_text=f'''# Stabilization milestone — {state} — 2026-10-20

The opt-in persistent prerequisite executor is implemented and evaluated. The failed Phase 9 study remains unchanged and its learner stays outside live autonomous policies. Its previous status is preserved in [PHASE9_STATUS.md](PHASE9_STATUS.md).

Read the [stabilization report](STABILIZATION_REPORT.md), [operations/handoff guide](STABILIZATION_OPERATIONS.md), [original protocol](STABILIZATION_PROTOCOL.md) and disclosed [fixture](STABILIZATION_AMENDMENT_1.md)/[navigation](STABILIZATION_AMENDMENT_2.md) amendments.

## Fresh-cohort outcomes

{chr(10).join(table)}

The final cohort used seeds 808,909,1001 with carried food, gathering, unavailable food, depleted targets and interrupted plans. Feasible goals exclude genuinely unavailable/depleted food; needs, scarcity and all action outcomes remain recorded. Generated JSON/plans, submitted/accepted requests, completed actions and achieved ingestion are distinct stages. These are selected-inhabitant scenario results, not a general population reliability guarantee.

The first partial attempt had an invalid competitor fixture. The second valid-fixture attempt exposed a real occupied-approach defect and missed water. Both remain preserved as failures. The repaired controller was tested on a new cohort with unchanged thresholds, not repeatedly tuned against the original held-out set. Route selection and prerequisite execution are authored, even for a model-selected goal.

## Continuous operation and verification

{chr(10).join(horizon)}

Finite food/water, regeneration zero, no body reset or silent replenishment. Save/resume at 120 seconds preserved source-pinned goals, inference budgets, navigation/schedules, native state and memories. Exact actual horizons, cutoffs, primary wall time and separate recorded-command parity costs are in the report. These are not 24-hour or long-term sustainability claims.

Full verification passed: **{passed}**. {testline}. Native checks and complete subprocess evidence: [stabilization_checks.json](../artifacts/stabilization_checks.json). Protected Phase 9 file hashes match: **{all(preservation.values())}**; its independent original audit is retained separately. Original native/durable runtime identities and validator semantics are unchanged.

## Handoff and remaining limits

Use `python -m underworld.stabilization init/attach/run/status` as documented. This is an explicit opt-in scheduler handoff; no existing Phase 8/9 world was silently switched or reset. The viewer can attach read-only. The legacy viewer time controller and Phase 7 supervisor do not automatically drive the new executor; its model calls use separate audited counters.

Crowd layouts, arbitrary cargo rearrangement/complex tasks, unavailable-water combinations, long-term supply and full-day operation remain outside this evidence. The host-side controller is not a newly verified AppContainer service. Native hashes and controller-journal checks are separate; journals and requests have finite quotas. No neural training, reproduction, speech, true 3D, consciousness, general intelligence or civilization-emergence claim was added. Phase 9's failed advancement gate was not changed.
'''
    (ROOT/'docs/STATUS.md').write_text(status_text,encoding='utf-8')
    sources=['underworld/stabilization.py','scripts/stabilization_common.py','scripts/stabilization_baseline.py','scripts/stabilization_evaluate.py',
             'scripts/stabilization_continuity.py','scripts/stabilization_report.py','scripts/verify_stabilization.py','tests/test_stabilization.py',
             'docs/STABILIZATION_PROTOCOL.md','docs/STABILIZATION_AMENDMENT_1.md','docs/STABILIZATION_AMENDMENT_2.md']
    for source in sources:
        target=ROOT/'artifacts/stabilization_sources'/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,target)
    write(ROOT/'artifacts/stabilization_source_manifest.json',dict(sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}))
    print(json.dumps(dict(heldout=evaluation['checks'],continuity=continuity['checks'],verification=passed,phase9_preserved=all(preservation.values())),indent=2))


if __name__=='__main__':main()
