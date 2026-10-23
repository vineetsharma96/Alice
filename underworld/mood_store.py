"""Copy-only F4 coordinator derived from the frozen atomic emotion coordinator."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json

from . import emotion_store as legacy, mood_affect, weather_store as weather
from .profile_derivation import derive,legacy_pins,ROOT


def sources():
    paths=set(legacy_pins())|{'underworld/profile_derivation.py','underworld/mood_affect.py','underworld/mood_store.py'}
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def _legacy_people(db):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='emotion_meta'").fetchone():
        return legacy.head(db)[2]
    return {}


def _resolve_agents(db,w,agents):
    known={e['entity_id'] for e in w.snapshot()['entities'] if e['kind']=='actor'}
    if agents is None:agents=sorted(known)
    if not agents or len(set(agents))!=len(agents) or not set(agents)<=known:raise ValueError('Select existing unique inhabitants')
    return agents


def _initial_people(db,w,agents,mode,params,connected):
    inherited=_legacy_people(db);people={}
    if isinstance(params,dict) and set(params)==set(agents):per_person=params
    else:per_person={a:params for a in agents}
    for a in agents:
        if a in inherited:
            s=deepcopy(inherited[a])
            if mode is not None:
                mood_affect.initial(w.observe_batch([a])[0],mode) # validate explicit profile selection
                s['mode']=mode
            origin=dict(kind='authored_initial_parameters_on_inherited_person',learned=False,
                        inherited_rule=s['rule'],inherited_updates=s['updates'])
            people[a]=mood_affect.decorate(s,per_person[a],connected,origin)
        else:people[a]=mood_affect.initial(w.observe_batch([a])[0],mode or 'learned',per_person[a],connected)
    return people


def _origin(db,policies):
    people=_legacy_people(db)
    cursor=policies.get('_scheduler',{}).get('cursor',0)
    if people:
        checksum=db.execute('SELECT hash FROM emotion_head WHERE id=1').fetchone()[0]
        cursor+=db.execute("SELECT COUNT(*) FROM emotion_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        return dict(kind='F0-F3_copy',parent_hash=checksum,scheduler_cursor=cursor)
    return dict(kind='weather_copy',scheduler_cursor=cursor)


_backend=derive('underworld._mood_store','underworld/emotion_store.py',[
    ("from . import emotion, weather_store as weather, weather_policy",
     "from . import mood_affect as emotion, weather_store as weather, weather_policy"),
    ("def attach(source, destination, agents=('agent-1',), mode='learned'):",
     "def attach(source, destination, agents=None, mode=None, temperament=None, connected=True):"),
    ("if not agents or len(set(agents)) != len(agents):raise ValueError('Select unique owners')",
     "if agents is not None and (not agents or len(set(agents)) != len(agents)):raise ValueError('Select unique owners')"),
    ("        people = {a:emotion.initial(w.observe_batch([a])[0], mode) for a in agents}",
     "        agents = _resolve_agents(db,w,agents)\n        people = _initial_people(db,w,agents,mode,temperament,connected)"),
    ("weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]))",
     "weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]), origin=weather.dumps(_origin(db,policies)))"),
    ("request_id='affect-'+logical_id", "request_id='affect-f4-'+logical_id"),
    ("f'{logical_id}:{agent}'", "f'f4:{logical_id}:{agent}'"),
    # Explicit occurrence counts guard every identifier substitution.
    ("'ALICE-EMOTION-1'", "'ALICE-MOOD-F4-1'",2),
    ('emotion_meta','mood_meta',4),
    ('emotion_head','mood_head',4),
    ('emotion_operations','mood_operations',6),
],dict(_resolve_agents=_resolve_agents,_initial_people=_initial_people,_origin=_origin))

_backend.sources=sources
for _name in ('attach','head','inspect','apply','commit','replay','token','JournalWorld'):
    globals()[_name]=getattr(_backend,_name)
