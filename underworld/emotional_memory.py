"""F5 private salience index into factual journal events; original authored rules."""
from copy import deepcopy
import math

from . import mood_affect as affect

RULE='alice-emotional-memory-f5-1'
MODES=('connected','disconnected','frozen')
LIMIT=32


def decorate(s,params=None,connected=True,origin=None,memory_mode='connected'):
    if memory_mode not in MODES:raise ValueError('Unknown emotional memory mode')
    # Retain existing F4 temperament exactly unless explicitly overridden.
    if 'temperament' not in s or params is not None:
        s=affect.decorate(s,params,connected,origin)
    else:s=deepcopy(s)
    if 'emotional_memory' in s:raise ValueError('Already has F5 memory; resume instead')
    s['emotional_memory']=dict(rule=RULE,mode=memory_mode,entries=[],encoded=0,evicted=0,
                              origin='new private index; historical events not retroactively encoded')
    return s


def initial(o,mode='learned',params=None,connected=True,memory_mode='connected'):
    return decorate(affect.initial(o,mode,params,connected),memory_mode=memory_mode)


def validate(s):
    affect.validate(s);m=s['emotional_memory']
    if m['rule']!=RULE or m['mode'] not in MODES:raise ValueError('Unsupported memory schema')
    if len(m['entries'])>LIMIT or len({e['event'] for e in m['entries']})!=len(m['entries']):
        raise ValueError('Memory index retention/identity bound')
    if any(type(m[k]) is not int or m[k]<0 for k in ('encoded','evicted')) or m['encoded']-m['evicted']!=len(m['entries']):
        raise ValueError('Memory accounting mismatch')
    for e in m['entries']:
        contexts={f'{r}/{t}/{c}' for r in ('rain','dry') for t in ('chilly','mild') for c in ('covered','open')}
        if e['context'] not in contexts or e['owner']!=s['owner'] or e['run_id']!=s['run_id'] or not 0<=e['start_tick']<e['end_tick']<=s['tick']:
            raise ValueError('Foreign or future memory')
        for k,lo,hi in [('salience',0,1),('outcome',-1,1),('confidence',0,1),('dt_s',0,1e9),('duration_s',0,1e9)]:
            if type(e[k]) not in (int,float) or not math.isfinite(e[k]) or not lo<=e[k]<=hi:
                raise ValueError('Invalid memory '+k)
        if e['dt_s']<=0 or e['duration_s']<=0:raise ValueError('Invalid memory clock')
    return s


def retrieve(s,key):
    rows=[]
    for e in s['emotional_memory']['entries']:
        if e['context']!=key:continue
        age=(s['tick']-e['end_tick'])*e['dt_s']
        weight=e['salience']*math.exp(-age/180)*min(e['duration_s']/10,1)
        if weight>1e-12:rows.append((e,weight))
    total=sum(w for _,w in rows)
    return dict(value=sum(e['outcome']*w for e,w in rows)/total if total else 0.,
                confidence=-math.expm1(-total),memories=[e['event'] for e,_ in rows],
                weights=[dict(event=e['event'],weight=w,outcome=e['outcome'],salience=e['salience']) for e,w in rows],
                rule=RULE,context=key,origin='retrieved own acquired journal links; authored weights')


def update(s,before,after,event_id,receipt=None,goal=None):
    result=affect.update(s,before,after,event_id,receipt,goal)
    if result is None:return None
    m=s['emotional_memory'];app=result['appraisal'];encoded=None
    if app['dt_s']>0 and m['mode']!='frozen' and s['mode']!='disabled':
        encoded=dict(event=event_id,owner=s['owner'],run_id=s['run_id'],
                     context=affect.cue(before),start_tick=int(before['tick']),end_tick=int(after['tick']),
                     dt_s=before['dt_s'],duration_s=app['dt_s'],outcome=app['outcome'],
                     salience=min(1.,.2+.4*app['harm']+.2*app['relief']+.2*app['surprise']),
                     confidence=1.,uncertainty='observed bodily interval; cause/intention not inferred',
                     observation_refs=list(result['observation_refs']),
                     receipt_ref=receipt.get('request_id') if receipt else None,
                     provenance='own native observations + linked journal appraisal')
        m['entries'].append(encoded);m['encoded']+=1
        selected=[];contexts=sorted({e['context'] for e in m['entries']});quota=LIMIT//len(contexts)
        for context in contexts:
            group=[e for e in m['entries'] if e['context']==context]
            salient=sorted(group,key=lambda e:(e['salience'],e['end_tick'],e['event']),reverse=True)[:quota//2]
            recent=sorted(group,key=lambda e:(e['end_tick'],e['event']),reverse=True)
            kept={e['event']:e for e in salient+recent[:quota-quota//2]}
            for e in recent:
                if len(kept)>=quota:break
                kept[e['event']]=e
            selected.extend(kept.values())
        m['evicted']+=len(m['entries'])-len(selected)
        m['entries']=sorted(selected,key=lambda e:(e['end_tick'],e['event']))
    result['emotional_memory']=dict(encoded=deepcopy(encoded),retained=len(m['entries']),
                                    evicted=m['evicted'],mode=m['mode'],rule=RULE)
    validate(s)
    return result


def influence(o,s,base):
    if o['agent_id']!=s['owner'] or o['run_id']!=s['run_id'] or int(o['tick'])!=s['tick']:
        raise ValueError('Foreign/stale memory query')
    p=retrieve(s,affect.cue(o));used=s['emotional_memory']['mode']!='disconnected'
    candidate=deepcopy(s)
    if used:candidate['associations'][affect.cue(o)]=dict(p,seconds=0,evidence=p['memories'])
    choice,log=affect.influence(o,candidate,base)
    log.update(emotional_memory=p,memory_connected=used,
               origin='acquired emotional memory + authored retrieval/routing' if used else 'unchanged F4 cue baseline; memory disconnected')
    return choice,log
