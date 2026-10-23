"""Original, offline F0-F3 appraisal. Inputs are one owner's native perceptions only.

Authored cue representation and update law; learned cue values start at zero.
This module has no world/database handles, LLM, shared lexicon or Phase9 learner.
"""
import math

RULE = 'alice-affect-1'


def clamp(x, low=0., high=1.):
    if not math.isfinite(x):
        raise ValueError('Nonfinite affect input')
    return max(low, min(high, x))


def signals(o):
    b = o['own_state']['body']; e = o['own_state'].get('weather', {})
    return dict(hunger=clamp(b['hunger']), thirst=clamp(b['thirst']),
                exhaustion=clamp(b['fatigue']), injury=clamp(1-b['health']),
                thermal=clamp(e.get('cold_burden', 0)), wetness=clamp(e.get('wetness', 0)))


def cue(o):
    e = o['own_state'].get('weather', {})
    # Authored coarse context, not a claim that storms are innately feared.
    return '/'.join(('rain' if e.get('rain', 'none') != 'none' else 'dry',
                     'chilly' if e.get('felt_temperature_c', 20) < 10 else 'mild',
                     'covered' if e.get('shelter_id') else 'open'))


def initial(o, mode='learned'):
    if mode not in ('learned', 'frozen', 'disconnected', 'disabled'):
        raise ValueError('Unknown emotional profile')
    return dict(schema=1, rule=RULE, owner=o['agent_id'], run_id=o['run_id'], mode=mode,
                tick=int(o['tick']), affect=dict(valence=0., arousal=0., control=.5),
                stress=0., body=signals(o), episodes=[], associations={}, recent=[],
                relationships={}, regulation={}, updates=0, last=None,
                caution_failures=0, caution_blocked_until=0,
                initial_bias='zero cue values; authored bodily drives, no feared species')


def validate(s):
    if s['rule'] != RULE or s['schema'] != 1:
        raise ValueError('Unsupported emotion rule/schema')
    if not math.isfinite(s['stress']) or not 0 <= s['stress'] <= 1:
        raise ValueError('Stress outside bounds')
    if not -1 <= s['affect']['valence'] <= 1:
        raise ValueError('Valence outside bounds')
    for key in ('arousal', 'control'):
        if not 0 <= s['affect'][key] <= 1:raise ValueError('Affect outside bounds')
    for value in s['body'].values():
        if not 0 <= value <= 1:raise ValueError('Body signal outside bounds')
    if len(s['episodes']) > 16 or len(s['recent']) > 64 or len(s['associations']) > 8:
        raise ValueError('Cognitive retention bound exceeded')
    for a in s['associations'].values():
        if not -1 <= a['value'] <= 1 or not 0 <= a['confidence'] <= 1:
            raise ValueError('Association outside bounds')
    return s


def prediction(s, key):
    a = s['associations'].get(key)
    return dict(value=a['value'], confidence=a['confidence'], memories=a['evidence'][-4:]) if a else dict(value=0., confidence=0., memories=[])


def appraisal(before, after, receipt, goal, expected):
    a, b = signals(before), signals(after)
    dt = (int(after['tick'])-int(before['tick']))*before['dt_s']
    injury_delta = max(0., b['injury']-a['injury'])
    thermal_delta = max(0., b['thermal']-a['thermal'])
    harm = max(injury_delta/max(dt*.0015, 1e-12), thermal_delta/max(dt*.012, 1e-12)) if dt else 0.
    relief = max(0., a['hunger']-b['hunger'])+max(0., a['thirst']-b['thirst'])
    safe = dt > 0 and b['thermal'] < .12 and injury_delta == 0
    outcome = clamp(-harm if harm > .01 else .3 if safe else 0., -1, 1)
    code = receipt.get('error_code', '') if receipt else ''
    classification = {'INSUFFICIENT_RESOURCE':'scarcity', 'OUT_OF_REACH':'approach_error',
                      'BUSY':'contention', 'STALE_OBSERVATION':'stale_observation',
                      'TARGET_UNAVAILABLE':'unavailable_not_proven_depleted'}.get(code, 'observed_outcome')
    food = max(0., a['hunger']-b['hunger'])
    water = max(0., a['thirst']-b['thirst'])
    relevant = food if goal and 'food' in goal else water if goal and 'water' in goal else 0.
    return dict(goal=goal, relevance=clamp(relevant*10), benefit=clamp(relevant*10),
                harm=clamp(harm), relief=clamp(relief*5), outcome=outcome,
                prediction=expected, surprise=abs(outcome-expected['value'])/2,
                predictability=expected['confidence'], controllability=.2 if classification=='scarcity' else .5,
                responsibility='unknown; intention not inferred', classification=classification,
                dt_s=dt, rule=RULE)


def update(s, before, after, event_id, receipt=None, goal=None):
    for o in (before, after):
        if o['agent_id'] != s['owner'] or o['run_id'] != s['run_id']:
            raise ValueError('Foreign emotional observation')
    if int(before['tick']) != s['tick'] or int(after['tick']) < s['tick']:
        raise ValueError('Missing or backward cognitive interval')
    if s['recent'] and s['recent'][-1] == event_id:
        return None
    key = cue(before); expected = prediction(s, key)
    app = appraisal(before, after, receipt, goal, expected)
    dt = app['dt_s']; old = dict(s['affect']); old_stress = s['stress']
    s['body'] = signals(after); body = s['body']
    discomfort = max(body['hunger'], body['thirst'], body['exhaustion']*.7,
                     body['injury'], body['thermal'])
    target = dict(valence=-discomfort, arousal=clamp(discomfort*.8+app['harm']*.2),
                  control=app['controllability'])
    alpha = -math.expm1(-dt/10)
    if s['mode'] != 'disabled':
        for k in target:s['affect'][k] += alpha*(target[k]-s['affect'][k])
        s['stress'] += -math.expm1(-dt/120)*(discomfort-s['stress'])
        s['episodes'] = [dict(e, intensity=e['intensity']*math.exp(-dt/20)) for e in s['episodes'] if e['intensity']*math.exp(-dt/20) > .01]
        if app['harm'] > .01 or app['relief'] > .01:
            s['episodes'].append(dict(cause=event_id, target=key, onset=int(after['tick']),
                                      harm=app['harm'], relief=app['relief'], intensity=max(app['harm'], app['relief']), confidence=1., origin='authored appraisal of observed change'))
        s['episodes'] = s['episodes'][-16:]
    learning = None
    if dt > 0 and s['mode'] in ('learned', 'disconnected'):
        a = s['associations'].setdefault(key, dict(value=0., seconds=0., confidence=0., evidence=[]))
        prior = a['value']; a['value'] += -math.expm1(-dt/30)*(app['outcome']-prior)
        a['seconds'] = min(1e6, a['seconds']+dt); a['confidence'] = 1-math.exp(-a['seconds']/60)
        a['evidence'] = (a['evidence']+[event_id])[-8:]
        learning = dict(cue=key, before=prior, after=a['value'], target=app['outcome'],
                        rule='time-weighted delta, tau30s; native injury/cold CHANGE, safety condition')
    s['recent'] = (s['recent']+[event_id])[-64:]; s['tick'] = int(after['tick']); s['updates'] += 1
    s['last'] = dict(event=event_id, observation_refs=[f"{o['run_id']}:{o['agent_id']}:{o['tick']}" for o in (before, after)],
                     appraisal=app, before=old, after=dict(s['affect']), stress_before=old_stress,
                     stress_after=s['stress'], learning=learning, memories=expected['memories'])
    validate(s)
    return s['last']


def influence(o, s, base):
    """Only a learned, bounded safety alternative to an otherwise idle action.

    Native weather/need urgency retains priority; no movement through hidden map.
    Feasibility is checked by the existing own-observation route planner + native.
    """
    from . import weather_policy as policy
    p = prediction(s, cue(o))
    log = dict(origin='learned_cue_value + authored alternative/routing', prediction=p,
               changed=False, baseline=base, reason='no eligible learned preference')
    if s['mode'] != 'learned' or not base or base['action'] != 'rest' or p['value'] >= -.12 or p['confidence'] < .2 or int(o['tick']) < s['caution_blocked_until']:
        return None, log
    body = o['own_state']['body']
    if max(body['hunger'], body['thirst']) >= .6 or o['own_state'].get('weather', {}).get('shelter_id'):
        return None, log
    roofs = [e for e in o['visible_entities'] if e['kind']=='lean_to']
    if roofs:
        target = min(roofs, key=lambda e:math.dist(e['position_m'], o['own_state']['position_m']))
        alternative = policy.go(o, target['position_m'], 'learned_caution')
        if alternative['action']=='move':
            log.update(changed=True, reason='negative personal cue expectation; own visible roof alternative')
            return alternative, log
    return None, log
