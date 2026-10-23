"""F4: one derived affect pipeline with declared immutable temperament.

The old stress integration is REPLACED, never run alongside a second mood engine.
Learned cue updates, fast affect and native authority are retained.
"""
from copy import deepcopy
import math

from .profile_derivation import derive

PRESETS={
    'balanced':dict(sensitivity=1.,rise_s=120.,recovery_s=180.,baseline=0.),
    'sensitive':dict(sensitivity=1.25,rise_s=60.,recovery_s=240.,baseline=0.),
    'calm':dict(sensitivity=.8,rise_s=180.,recovery_s=90.,baseline=0.),
}


def temperament(value=None):
    if value is None:value='balanced'
    if isinstance(value,str):
        if value not in PRESETS:raise ValueError('Unknown temperament preset')
        value=PRESETS[value]
    if not isinstance(value,dict) or set(value)!=set(PRESETS['balanced']):raise ValueError('Exact temperament fields required')
    limits=dict(sensitivity=(.5,1.5),rise_s=(30,600),recovery_s=(30,600),baseline=(-.1,.1))
    for key,(low,high) in limits.items():
        v=value[key]
        if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high:
            raise ValueError('Invalid temperament '+key)
    return {k:float(v) for k,v in value.items()}


def mood_value(stress,t):
    return max(-1.,min(1.,t['baseline']-stress))


def decorate(s,params=None,connected=True,origin=None):
    if type(connected) is not bool:raise ValueError('Mood connection requires bool')
    s=deepcopy(s)
    s['schema']=2;s['rule']='alice-mood-f4-1'
    s['temperament']=temperament(params);s['mood_connected']=connected
    s['temperament_origin']=origin or dict(kind='authored_initial_parameters',learned=False)
    s['mood']=dict(valence=mood_value(s['stress'],s['temperament']),source='slow_body_derived_stress')
    return s


def validate_mood(s):
    t=temperament(s['temperament'])
    if type(s['mood_connected']) is not bool or s['temperament_origin']['learned'] is not False:
        raise ValueError('Unsupported mood/temperament provenance')
    if s['mood']['valence']!=mood_value(s['stress'],t):raise ValueError('Mood/stress inconsistency')


def integrate(s,discomfort,dt):
    t=s['temperament'];target=max(0.,min(1.,t['sensitivity']*max(0.,discomfort-.3)/.7))
    tau=t['rise_s'] if target>s['stress'] else t['recovery_s']
    s['stress']+=-math.expm1(-dt/tau)*(target-s['stress'])
    s['mood']['valence']=mood_value(s['stress'],t)


def threshold(s):
    return -.12+.04*s['stress'] if s['mood_connected'] else -.12


_profile=derive('underworld._mood_affect','underworld/emotion.py',[
    ("RULE = 'alice-affect-1'","RULE = 'alice-mood-f4-1'"),
    ("return dict(schema=1, rule=RULE", "return dict(schema=2, rule=RULE"),
    ("s['schema'] != 1", "s['schema'] != 2"),
    ("def validate(s):\n", "def validate(s):\n    _validate_mood(s)\n"),
    ("        s['stress'] += -math.expm1(-dt/120)*(discomfort-s['stress'])", "        _integrate_mood(s,discomfort,dt)"),
    ("p['value'] >= -.12", "p['value'] >= _mood_threshold(s)"),
    ("changed=False, baseline=base, reason='no eligible learned preference')",
     "changed=False, baseline=base, reason='no eligible learned preference', mood_stress=s['stress'], caution_threshold=_mood_threshold(s), mood_connected=s['mood_connected'], origin_detail='authored bounded mood influence on personal learned cue')"),
    ("stress_after=s['stress'], learning=learning, memories=expected['memories'])",
     "stress_after=s['stress'], learning=learning, memories=expected['memories'], mood_before=_mood_value(old_stress,s['temperament']), mood_after=dict(s['mood']), temperament=dict(s['temperament']), temperament_origin=s['temperament_origin'])"),
],dict(_integrate_mood=integrate,_validate_mood=validate_mood,_mood_threshold=threshold,_mood_value=mood_value))


def initial(observation,mode='learned',params=None,connected=True):
    return decorate(_profile.initial(observation,mode),params,connected)


validate=_profile.validate
update=_profile.update
influence=_profile.influence
signals=_profile.signals
prediction=_profile.prediction
cue=_profile.cue
