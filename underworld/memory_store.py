"""F5 copy-only atomic coordinator; original native and F4 journals stay intact."""
from copy import deepcopy
import hashlib
import json

from . import mood_store as parent,emotional_memory,weather_store as weather
from .profile_derivation import derive,ROOT


def sources():
    paths=set(parent.sources())|{'underworld/emotional_memory.py','underworld/memory_store.py'}
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def _people(db,w,agents,mode,params,connected,memory_mode):
    has_parent=db.execute("SELECT 1 FROM sqlite_master WHERE name='mood_meta'").fetchone()
    inherited=parent.head(db)[2] if has_parent else parent._legacy_people(db)
    selected=parent._resolve_agents(db,w,agents);people={}
    per_person=params if isinstance(params,dict) and set(params)==set(selected) else {a:params for a in selected}
    for a in selected:
        if a in inherited:
            s=deepcopy(inherited[a])
            if mode is not None:
                emotional_memory.initial(w.observe_batch([a])[0],mode)
                s['mode']=mode
            people[a]=emotional_memory.decorate(s,per_person[a],connected,memory_mode=memory_mode)
        else:people[a]=emotional_memory.initial(w.observe_batch([a])[0],mode or 'learned',per_person[a],connected,memory_mode)
    return people


def _origin(db,policies):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='mood_meta'").fetchone():
        _,_,_,meta=parent.head(db)
        cursor=json.loads(meta['origin'])['scheduler_cursor']
        cursor+=db.execute("SELECT COUNT(*) FROM mood_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        return dict(kind='F4_copy',parent_hash=db.execute('SELECT hash FROM mood_head WHERE id=1').fetchone()[0],scheduler_cursor=cursor)
    return parent._origin(db,policies)


_backend=derive('underworld._memory_store','underworld/emotion_store.py',[
    ('from . import emotion, weather_store as weather, weather_policy',
     'from . import emotional_memory as emotion, weather_store as weather, weather_policy'),
    ("def attach(source, destination, agents=('agent-1',), mode='learned'):",
     "def attach(source, destination, agents=None, mode=None, temperament=None, connected=True, memory_mode='connected'):"),
    ("if not agents or len(set(agents)) != len(agents):raise ValueError('Select unique owners')",
     "if agents is not None and (not agents or len(set(agents)) != len(agents)):raise ValueError('Select unique owners')"),
    ('        people = {a:emotion.initial(w.observe_batch([a])[0], mode) for a in agents}',
     '        people = _people(db,w,agents,mode,temperament,connected,memory_mode)'),
    ("weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]))",
     "weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]), origin=weather.dumps(_origin(db,policies)))"),
    ("request_id='affect-'+logical_id","request_id='affect-f5-'+logical_id"),
    ("f'{logical_id}:{agent}'","f'f5:{logical_id}:{agent}'"),
    ("'ALICE-EMOTION-1'","'ALICE-MEMORY-F5-1'",2),
    ('emotion_meta','memory_meta',4),('emotion_head','memory_head',4),('emotion_operations','memory_operations',6),
],dict(_people=_people,_origin=_origin))
_backend.sources=sources
for _name in ('attach','head','inspect','apply','commit','replay','token','JournalWorld'):
    globals()[_name]=getattr(_backend,_name)
