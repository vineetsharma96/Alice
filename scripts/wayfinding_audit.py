"""Independent native-outcome, source, cost and inventory verification for H4."""
import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from underworld import storage, wayfinding as wf  # noqa: E402
from community_audit import registered, read, check_experience  # noqa: E402
from wayfinding_study import SEEDS, ARMS  # noqa: E402


def verify_final(report):
    path = Path(report['path'])
    actual = wf.audit(path)
    if actual != report['final']['audit'] or not storage.replay(path)['replay_matches']:
        raise ValueError('H4 private final state/replay mismatch')
    with closing(storage._connect(path, readonly=True)) as db:
        world, _, _, _ = storage._head(db)
        world.check_invariants()
        if db.execute('SELECT COUNT(*) FROM cognition_calls').fetchone()[0]:
            raise ValueError('unexpected model use')
        for payload, in db.execute("SELECT payload FROM development_records WHERE kind='experience'"):
            if json.loads(payload)['receipt']['status'] != 'completed':
                raise ValueError('noncompleted native action in confirmation')
    return actual


def outcome(db, execution):
    for movement in execution.get('route', []):
        check_experience(db, movement)
    actions = [check_experience(db, a) for a in execution['actions']]
    if not execution['goal_completed']:
        if actions:
            raise ValueError('unexpected partial native attempt; investigate separately')
        return False
    if execution.get('used_carried'):
        consumed = actions[0]
        need = 'thirst' if consumed['request']['action_type'] == 'drink' else 'hunger'
        if consumed['before']['own_state']['body'][need] <= consumed['after']['own_state']['body'][need]:
            raise ValueError('carried consumption did not relieve a need')
        return True
    if [a['request']['action_type'] for a in actions[:2]] != ['inspect', 'gather'] or actions[2]['request']['action_type'] not in ('eat', 'drink'):
        raise ValueError('goal lacks inspect/gather/consume sequence')
    inspected, gathered, consumed = actions
    source = gathered['request']['target_ids'][0]
    if inspected['request']['target_ids'] != [source] or source != execution['source']:
        raise ValueError('goal source receipt mismatch')
    action = consumed['request']['action_type']
    material, need = ('water', 'thirst') if action == 'drink' else ('food', 'hunger')
    gain = int(gathered['after']['own_state']['inventory_ug'].get(material, 0)) - int(gathered['before']['own_state']['inventory_ug'].get(material, 0))
    relief = consumed['before']['own_state']['body'][need] - consumed['after']['own_state']['body'][need]
    if gain != 50000000 or consumed['receipt']['observable_effects']['description'] != 'ingested_ug=50000000' or relief <= 0:
        raise ValueError('completed requests did not achieve acquisition/need goal')
    return True


def audit(study, registration):
    report = read(study)
    if report['split'] != 'confirmation' or len(report['cases']) != 5 or {c['seed'] for c in report['cases']} != set(SEEDS):
        raise ValueError('exact held-out H4 cohort missing')
    if not registered(registration):
        raise ValueError('prospective H4 source mismatch')
    for name in ('developmental_h1_registration_repaired.json', 'developmental_h2_registration.json', 'h3_native_registration.json', 'living_world_g_registration.json'):
        if not registered(ROOT / 'artifacts' / name):
            raise ValueError('historical sources changed')
    counts = {a: [0, 0] for a in ARMS}
    costs = []
    need_counts = []
    durations = []
    scarce = 0
    identity = 0
    for case in report['cases']:
        if len(case['scenarios']) != 2 or case['wall_s'] > 900:
            raise ValueError('scenario inventory or seed cap mismatch')
        for scenario in case['scenarios']:
            setup = scenario['setup']
            target = setup['target_operator_only']
            if any(e['entity_id'] == target for e in setup['recipient_before_message']['visible_entities']):
                raise ValueError('target was not hidden at the hub')
            if len(scenario['arms']) != 4 or {a['arm'] for a in scenario['arms']} != set(ARMS):
                raise ValueError('communication comparator inventory mismatch')
            if {a['initial_head'] for a in scenario['arms']} != {setup['snapshot']['state_hash']}:
                raise ValueError('arms lack identical native starts')
            for arm in scenario['arms']:
                actual = verify_final(arm)
                if not arm['fresh_process'] or arm['initial_memory_hashes'] != actual['h4_memory_hashes']:
                    raise ValueError('resume/frozen learning gate failed')
                if arm['report']['verified']:
                    raise ValueError('unseen report was presented as confirmed')
                with closing(storage._connect(Path(arm['path']), readonly=True)) as db:
                    speech = check_experience(db, arm['speech'])
                    if arm['arm'] == 'muted':
                        if speech['request']['action_type'] != 'rest' or arm['report']['location'] is not None:
                            raise ValueError('muted comparator delivered location')
                    else:
                        if speech['request']['action_type'] != 'speak' or speech['request']['target_ids'] or set(speech['request']['parameters']) != {'text'}:
                            raise ValueError('signal leaks a target/coordinate or lacks native speech')
                        message = arm['report']['message']
                        if message['source_event_seq'] not in speech['native_events']:
                            raise ValueError('report is not this native delivery')
                    if arm['arm'] == 'identity' and arm['report']['location'] is not None:
                        raise ValueError('resource word was treated as location')
                    success = outcome(db, arm['execution'])
                    if success and arm['execution']['source'] != target:
                        raise ValueError('credited an unrelated source')
                    if success and arm['arm'] == 'enabled':
                        confirmation = arm['execution'].get('confirmation')
                        if not confirmation or not arm['execution']['report_confirmed']:
                            raise ValueError('goal lacks durable report confirmation')
                        row = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=?',
                                         (confirmation['record_id'], 'agent-2')).fetchone()
                        if not row or dict(json.loads(row[0]), record_id=confirmation['record_id']) != confirmation:
                            raise ValueError('report confirmation differs from persistent evidence')
                if arm['execution']['protective_fallback']:
                    raise ValueError('hidden protective fallback')
                counts[arm['arm']][0] += success
                counts[arm['arm']][1] += 1
                travel = sum(math.dist(a['before']['own_state']['position_m'], a['after']['own_state']['position_m']) for a in arm['execution']['route'])
                costs.append({'seed': case['seed'], 'site': setup['site_index_operator_only'], 'arm': arm['arm'],
                              'receiver_travel_m': travel, 'receiver_native_requests': len(arm['execution']['route']) + len(arm['execution']['actions']),
                              'curiosity_fallback': arm['execution']['curiosity_fallback'],
                              'missed_feasible_first_site_opportunity': not success,
                              'scout_travel_m': sum(math.dist(a['before']['own_state']['position_m'], a['after']['own_state']['position_m']) for a in setup['scout_route'])})
                durations.append({'seed': case['seed'], 'arm': arm['arm'], 'site': setup['site_index_operator_only'],
                                  'initial_simulated_s': arm['initial_simulated_s'], 'end_simulated_s': arm['final']['snapshot']['simulated_time_s'],
                                  'wall_s': arm['wall_s'], 'living_bodies': sum(b['alive'] for b in arm['final']['bodies'])})
        scarcity = case['scarcity']
        verify_final(scarcity)
        if scarcity['execution']['goal_completed'] or scarcity['execution']['report_confirmed'] or scarcity['execution']['actions']:
            raise ValueError('depletion was credited or provoked an invalid gather')
        scarce += 1
        for window in case['need_windows']:
            verify_final(window)
            if not window['fresh_process'] or window['initial_audit']['h4_memory_hashes'] != window['final']['audit']['h4_memory_hashes']:
                raise ValueError('need-window frozen/resume mismatch')
            complete = 0
            with closing(storage._connect(Path(window['path']), readonly=True)) as db:
                for step in window['steps']:
                    for movement in step.get('revisit_route', []):
                        check_experience(db, movement)
                    if step['execution']:
                        if step['execution']['assigned'] or not step['decision']['goal']:
                            raise ValueError('assigned action credited as own-need selection')
                        goal = step['decision']['goal']
                        if step['decision']['needs'][goal['need']] < .45:
                            raise ValueError('goal lacked the declared native need')
                        complete += outcome(db, step['execution'])
                    else:
                        check_experience(db, step['inspection_or_rest'])
            if complete != window['self_selected_completed'] or window['milestones'][0]['decisions'] != 2 or window['milestones'][1]['decisions'] != 6:
                raise ValueError('need-window count/continuation mismatch')
            need_counts.append({'seed': case['seed'], 'frozen': window['frozen'], 'completed': complete,
                                'start_simulated_s': case['training']['snapshot']['simulated_time_s'],
                                'end_simulated_s': window['final']['snapshot']['simulated_time_s'],
                                'inquiries': sum(s['information_inquiries'] for s in window['steps']),
                                'source_revisits': sum(bool(s.get('revisit_route')) for s in window['steps']),
                                'native_need_relief': sum(s['execution'].get('need_relief', 0) for s in window['steps'] if s['execution']),
                                'final_body': next(b['body'] for b in window['final']['bodies'] if b['id'] == 'agent-2')})
        identity_path = Path(case['need_windows'][0]['path']).parent / f'{case["seed"]}-identity.sqlite'
        verify_final(dict(case['identity'], path=str(identity_path)))
        if not case['identity']['fresh_process']:
            raise ValueError('identity evaluation did not resume in a fresh process')
        for trial in case['identity']['trials']:
            with closing(storage._connect(identity_path, readonly=True)) as db:
                inspected = check_experience(db, trial['inspection'])
                if inspected['receipt']['observable_effects']['description'].split(':')[0] != trial['target_operator_only'] or trial['location_report']['location'] is not None:
                    raise ValueError('identity/location separation failed')
                identity += 1
        if case['need_windows'][0]['steps'][0]['decision']['needs'] != case['need_windows'][1]['steps'][0]['decision']['needs']:
            raise ValueError('prediction ablation did not begin at the same native needs')
    rates = {a: n / d for a, (n, d) in counts.items()}
    if any(abs(rates[a] - report['summary']['rates'][a]) > 1e-12 for a in ARMS):
        raise ValueError('reported metrics do not match native effects')
    improved = sum(sum(a['execution']['goal_completed'] for s in c['scenarios'] for a in s['arms'] if a['arm'] == 'enabled') >
                   sum(a['execution']['goal_completed'] for s in c['scenarios'] for a in s['arms'] if a['arm'] == 'scrambled') for c in report['cases'])
    communication = (rates['enabled'] >= .8 and all(rates['enabled'] - rates[a] >= .2 - 1e-12 for a in ('muted', 'scrambled'))
                     and improved >= 4 and identity == 10 and scarce == 5)
    need_gate = all(n['completed'] >= 1 if not n['frozen'] else n['completed'] == 0 for n in need_counts)
    return {'verified': True, 'communication_gate': communication, 'need_policy_gate': need_gate,
            'h4_gate': bool(communication and need_gate), 'counts': counts, 'rates': rates,
            'scarcity_checked': scarce, 'identity_checks': identity, 'costs': costs,
            'improved_over_scrambled_seeds': improved,
            'need_windows': need_counts, 'durations': durations, 'study_wall_s': report['wall_s'],
            'limits': 'Assigned remote-water task, authored scout/landmarks/executor; engineered need scheduler separately evaluated. No H5 or independent-intelligence claim.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True)
    p.add_argument('--registration', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.study, args.registration)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['verified'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
