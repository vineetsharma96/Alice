"""Copy-only UW10W integrated life, using the frozen atomic writer contract."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import math

from . import memory_store, mood_store, life_affect, weather_store as weather
from . import communication_f9 as communication
from .profile_derivation import derive, ROOT


def sources():
    paths=set(memory_store.sources())|{
        'underworld/life_affect.py','underworld/life_store.py',
        'underworld/relationships_f6.py','underworld/others_f7.py',
        'underworld/others_store_f7.py','underworld/regulation_f8.py',
        'underworld/communication_f9.py','underworld/social_emotions_f10.py',
        'underworld/identity_values_f11.py'}
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}


def _people(db,w,agents,mode):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='memory_meta'").fetchone():
        inherited=memory_store.head(db)[2]
    else:
        inherited=memory_store._people(db,w,agents,None,None,True,'connected')
    selected=mood_store._resolve_agents(db,w,agents)
    return {a:life_affect.decorate(inherited[a],mode) for a in selected}


def _origin(db,policies):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='memory_meta'").fetchone():
        meta=memory_store.head(db)[3]
        cursor=json.loads(meta['origin'])['scheduler_cursor']
        cursor+=db.execute("SELECT COUNT(*) FROM memory_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        return dict(kind='F5_copy',scheduler_cursor=cursor)
    return memory_store._origin(db,policies)


def _action(w,command,logical_id,emit):
    agent=command['agent'];choice=command['choice'];o=w.observe_batch([agent])[0]
    request=dict(schema_version=1,run_id=o['run_id'],request_id='life-'+logical_id,
        agent_id=agent,observation_version=o['tick'],action_type=choice['action'],
        target_ids=choice['targets'],parameters=choice['parameters'],requested_duration=choice['duration'])
    receipt=emit(dict(kind='submit',request=request,principal=agent))
    accepted=receipt['status']=='accepted'
    if accepted:
        emit(dict(kind='step',ticks=math.ceil(choice['duration']/o['dt_s'])))
        receipt=next(r for r in w.observe_batch([agent])[0]['recent_action_results'] if r['request_id']==request['request_id'])
    return dict(before=o,choice=choice,request=request,accepted=accepted,receipt=receipt,after=w.observe_batch([agent])[0])


def _context(people,command,result,influence):
    """Bind one terminal policy/assigned action to its actual owner's interval."""
    if not isinstance(result,dict) or 'request' not in result:return
    request=result['request'];agent=request['agent_id'];receipt=result['receipt']
    if agent not in people:return
    s=people[agent];x=s['life'];s['_life_action']=request['action_type']
    if command['kind']=='emotion-policy':
        x['decisions']+=1
        x['last_decision']=dict(tick=result['before']['tick'],choice=result['choice'],
                                receipt=receipt,influence=deepcopy(influence))
    if result['choice']['goal']=='search_observed_supplies':
        x['search_steps']+=1;x['search_index']=influence['search_waypoint']
    if x['mode']=='frozen' or s['mode'] in ('disabled','frozen'):return
    if receipt['status']!='completed':return
    if request['action_type']=='speak':
        o=result['before'];meaning=life_affect._meaning(o)
        partners=sorted(e['entity_id'] for e in o['visible_entities'] if e['kind']=='actor' and e['entity_id']!=agent
                        and math.dist(e['position_m'],o['own_state']['position_m'])<=o['hearing_range_m'])
        if meaning and partners and request['parameters'].get('text','').startswith('sig-'):
            preview=deepcopy(x['communication'])
            sent=communication.emit(preview,meaning,partners[0],'emit:'+request['request_id'])
            if sent['token']==request['parameters']['text']:
                x['communication']=preview;x['last_signal']=int(result['after']['tick'])
    if request['action_type']=='give':x['last_social']=int(result['after']['tick'])


_backend=derive('underworld._life_store','underworld/emotion_store.py',[
    ('from . import emotion, weather_store as weather, weather_policy',
     'from . import life_affect as emotion, weather_store as weather, weather_policy'),
    ("def attach(source, destination, agents=('agent-1',), mode='learned'):",
     "def attach(source, destination, agents=None, mode='connected'):"),
    ("if not agents or len(set(agents)) != len(agents):raise ValueError('Select unique owners')",
     "if agents is not None and (not agents or len(set(agents)) != len(agents)):raise ValueError('Select unique owners')"),
    ('        people = {a:emotion.initial(w.observe_batch([a])[0], mode) for a in agents}',
     '        people = _people(db,w,agents,mode)'),
    ("weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]))",
     "weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]), origin=weather.dumps(_origin(db,policies)))"),
    ("    elif command['kind'] in ('step', 'submit', 'force', 'policy', 'cohort'):",
     "    elif command['kind']=='life-act':\n        result=_action(w,command,logical_id,emit)\n    elif command['kind'] in ('step', 'submit', 'force', 'policy', 'cohort'):"),
    ('    updates = {}','    _context(people,command,result,influence)\n    updates = {}'),
    ('    return dict(native=result, influence=influence, updates=updates)',
     "    for s in people.values():s.pop('_life_action',None)\n    return dict(native=result, influence=influence, updates=updates)"),
    ("request_id='affect-'+logical_id","request_id='life-policy-'+logical_id"),
    ("f'{logical_id}:{agent}'","f'life:{logical_id}:{agent}'"),
    ("'ALICE-EMOTION-1'","'ALICE-LIFE-1'",2),
    ('emotion_meta','life_meta',4),('emotion_head','life_head',4),('emotion_operations','life_operations',6),
],dict(_people=_people,_origin=_origin,_action=_action,_context=_context))
_backend.sources=sources
for _name in ('attach','head','inspect','apply','commit','replay','token','JournalWorld'):
    globals()[_name]=getattr(_backend,_name)


def act(path,agent,choice,logical_id):
    return commit(path,dict(kind='life-act',agent=agent,choice=choice),logical_id)


def next_turn(path):
    """Resume the inherited all-inhabitant cursor; no wall-clock decay."""
    with closing(weather.connect(path)) as db:
        w,_,people,meta=head(db)
        cursor=json.loads(meta['origin'])['scheduler_cursor']
        cursor+=db.execute("SELECT COUNT(*) FROM life_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
        agents=sorted(people)
        alive={e['entity_id'] for e in w.snapshot()['entities'] if e['kind']=='actor' and e['alive']}
        candidates=[agents[(cursor+i)%len(agents)] for i in range(len(agents))]
        return next((a for a in candidates if a in alive),None),cursor


# New-world-only enrollment of existing native ecology/thermal/culture mechanics.
# This does not change a checkpoint or reinterpret any historical world format.
_initializer=derive('underworld._life_initial','underworld/weather_store.py',[
    ('    checkpoint = w.checkpoint()',
     "    w.configure_thermal()\n    w.configure_culture(seed)\n    w.configure_ecology(forage_kg=2,regeneration_kg_s=0)\n    checkpoint = w.checkpoint()"),
])
initialize_source=_initializer.initialize
