"""One F0–F12 update path, driven exclusively by one owner's native perceptions.

The original F5 mood engine is authoritative. Social modules add bounded
beliefs and action preferences, not a second affect engine. All motor choices
and feedback mappings are authored; associations are acquired from experience.
"""
from copy import deepcopy
import math

from . import emotional_memory as memory, relationships_f6 as relations
from . import others_f7 as inference, regulation_f8 as regulation
from . import communication_f9 as communication, social_emotions_f10 as social
from . import identity_values_f11 as values, weather_policy as policy
from .others_store_f7 import public_envelope_from_native

RULE = 'alice-integrated-life-1'
MODES = ('connected', 'disconnected', 'frozen', 'relationships_disabled', 'shuffled')


def decorate(person, mode='connected'):
    if mode not in MODES:raise ValueError('Unknown integration mode')
    s = deepcopy(person)
    if 'life' in s:raise ValueError('Already integrated; resume instead')
    a, run = s['owner'], s['run_id']
    s['life'] = dict(rule=RULE, mode=mode, relationships={}, inferences={},
                     regulation=regulation.initial(a, run),
                     communication=communication.initial(a, run),
                     social=social.initial(a, run), values=values.initial(a, run, []),
                     social_cursor=0, heard_cursor=0, last_signal=-1000000,
                     last_social=-1000000, decisions=0, last_decision=None,
                     deliveries=0, grounded=0, help_received=0,search_steps=0,search_index=0)
    return s


def initial(o, mode='learned'):
    return decorate(memory.initial(o, mode))


def validate(s):
    memory.validate(s); x = s['life']
    if x['rule'] != RULE or x['mode'] not in MODES:raise ValueError('Unsupported life profile')
    for key, module in [('regulation', regulation), ('communication', communication),
                        ('social', social), ('values', values)]:
        state=x[key];module.validate(state)
        if (state['owner'], state['run_id']) != (s['owner'], s['run_id']):
            raise ValueError('Foreign integrated private state')
    if len(x['relationships'])>63 or len(x['inferences'])>63:raise ValueError('Social population budget')
    for other,r in x['relationships'].items():
        relations.validate(r)
        if (r['owner'],r['other'])!=(s['owner'],other):raise ValueError('Foreign relationship')
    for other,r in x['inferences'].items():
        inference.validate(r)
        if (r['observer'],r['target'])!=(s['owner'],other):raise ValueError('Foreign inference')
    for key in ('social_cursor','heard_cursor','decisions','deliveries','grounded','help_received'):
        if type(x[key]) is not int or x[key]<0:raise ValueError('Invalid integrated counter')
    return s


def _meaning(o):
    """Own bodily co-occurrence labels; never the speaker's hidden intention."""
    b=o['own_state']['body'];e=o['own_state'].get('weather',{})
    if max(b['hunger'],b['thirst'],b['fatigue'],1-b['health'],e.get('cold_burden',0))>=.6:
        return 'distress'
    if max(b['hunger'],b['thirst'],b['fatigue'],1-b['health'],e.get('cold_burden',0))<.5:
        return 'calm'
    return None


def _event(s, ident, predicate, subject, other, kind='own_observation'):
    return dict(evidence_id=ident,kind=kind,owner=s['owner'],run_id=s['run_id'],
                provenance='learned',predicate=predicate,subject=subject,value=True,other=other)


def _value(s, ident, value, outcome, context, success=True):
    x=s['life'];state=x['values']
    values.observe_event(state,dict(evidence_id=ident,kind='native_outcome',owner=s['owner'],
        run_id=s['run_id'],provenance='native',status='succeeded' if success else 'failed',
        value=value,outcome=outcome,context=[context],source=ident))
    values.revise_summary(state,dict(text='Observed personal outcomes',claims=list(state['acquired_preferences']),
                                    contexts=[context]),ident)


def update(s,before,after,event_id,receipt=None,goal=None):
    result=memory.update(s,before,after,event_id,receipt,goal)
    x=s['life']; frozen=x['mode']=='frozen' or s['mode'] in ('disabled','frozen')
    if frozen:return result
    # One action interval, supplied by the atomic coordinator. No segment-wide
    # or reconstructed private target state is used as a learning outcome.
    if receipt and receipt.get('agent_id')==s['owner']:
        action=after['own_state'].get('action_type')
        description=receipt.get('observable_effects',{}).get('description','')
        # Receipt's request ID is matched by the coordinator's action context.
        action=s.get('_life_action',action)
        elapsed=(int(after['tick'])-int(before['tick']))*before['dt_s']
        if action in ('rest','move'):
            regulation.observe_outcome(x['regulation'],before,after,dict(
                request_id=receipt['request_id'],status=receipt['status'],action_type=action,
                result={},estimated_cost_s=elapsed))
        b,a=before['own_state']['body'],after['own_state']['body']
        if action in ('eat','drink') and receipt['status']=='completed':
            key='hunger' if action=='eat' else 'thirst'
            if b[key]>a[key]:_value(s,'native:'+receipt['request_id'],'sustenance',action,memory.affect.cue(before))
        if action=='rest' and receipt['status']=='completed' and b['fatigue']>a['fatigue']:
            _value(s,'native:'+receipt['request_id'],'recovery','rest',memory.affect.cue(before))
        if action=='give' and receipt['status']=='completed' and description.startswith('gave:'):
            _value(s,'native:'+receipt['request_id'],'care','give',memory.affect.cue(before))
    # Native social reports are symmetric. Only an actual own inventory gain
    # identifies receiving help; giving must not teach trust in the recipient.
    gains={k:int(v)-int(before['own_state']['inventory_ug'].get(k,0))
           for k,v in after['own_state']['inventory_ug'].items()}
    reports=[r for r in after.get('social_reports',[]) if int(r['source_event_seq'])>x['social_cursor']]
    for r in reports:
        x['social_cursor']=max(x['social_cursor'],int(r['source_event_seq']))
        other=r['other'];kind=r['kind'];ident='social:'+r['source_event_seq']
        if other==s['owner'] or kind not in relations.KINDS:continue
        if kind=='resource_given' and not any(v>0 for v in gains.values()):continue
        if x['mode']!='relationships_disabled':
            state=x['relationships'].setdefault(other,relations.initial(s['owner'],other))
            relations.observe(state,dict(observer=s['owner'],other=other,kind=kind,
                source_event_seq=r['source_event_seq'],tick=int(r['tick'])))
        if kind=='resource_given':
            x['help_received']+=1
            for predicate in ('received_help','recognized_benefit'):
                social.observe_event(x['social'],_event(s,ident+':'+predicate,predicate,ident,other,'relationship'))
    # F7 accepts a narrow public envelope, never private actor body/mood/inventory.
    for e in after['visible_entities']:
        other=e['entity_id']
        if e['kind']!='actor' or other==s['owner']:continue
        envelope=public_envelope_from_native(after,other)
        state=x['inferences'].setdefault(other,inference.initial(s['owner'],other))
        seen={r['source_event_id'] for r in state['evidence']}
        for channel in ('visible_cues','social_reports'):
            envelope[channel]=[r for r in envelope[channel] if r['source_event_id'] not in seen]
        if envelope['visible_cues'] or envelope['social_reports']:inference.infer(state,envelope)
    for r in after.get('audible_reports',[]):
        seq=int(r['source_event_seq'])
        if seq<=x['heard_cursor']:continue
        x['heard_cursor']=seq
        token=r['text'];speaker=r['speaker_id']
        if not token.startswith('sig-') or len(token)!=16 or speaker==s['owner']:continue
        if x['mode']=='shuffled':
            # Deterministic loss of token/meaning association; private feedback
            # remains unchanged and never consults the speaker's dictionary.
            import hashlib
            token='sig-'+hashlib.sha256((token+str(seq)).encode()).hexdigest()[:12]
        communication.receive(x['communication'],speaker,token,'heard:'+str(seq))
        x['deliveries']+=1
        meaning=_meaning(after)
        if meaning:
            communication.learn_from_feedback(x['communication'],token,meaning,True,'ground:'+str(seq),speaker)
            x['grounded']+=1
    validate(s)
    if result is not None:result['integrated']=dict(deliveries=x['deliveries'],grounded=x['grounded'],
        relationships=len(x['relationships']),inferences=len(x['inferences']),
        social_states=sorted(x['social']['states']),origin='native own intervals and public co-occurrence')
    return result


def influence(o,s,base):
    alternate,log=memory.influence(o,s,base)
    x=s['life'];trace=dict(memory=deepcopy(log),relationship=None,inference=None,
                          regulation=None,communication=None,social=None,values=None)
    log['integrated']=trace
    if x['mode']=='disconnected' or s['mode'] in ('disabled','disconnected'):return alternate,log
    if alternate is not None:return alternate,log
    body=o['own_state']['body'];env=o['own_state'].get('weather',{})
    if base and base['goal'] in ('unavailable_food','unavailable_water') and x['search_steps']<96:
        # A finite authored sweep uses only known bounds and local routes. It
        # does not insert an unseen resource location into personal memory.
        bounds=o['world_bounds_m'];index=x['search_index']
        points=[[2+(bounds['width']-4)*i/3,2+(bounds['height']-4)*j/3]
                for i in range(4) for j in (range(4) if i%2==0 else range(3,-1,-1))]
        q=points[index%len(points)]
        if math.dist(o['own_state']['position_m'],q)<1:
            index+=1;q=points[index%len(points)]
        choice=policy.go(o,q,'search_observed_supplies')
        log.update(changed=True,origin='authored bounded supply search fallback; no learned intelligence',
                   search_step=x['search_steps'],search_waypoint=index,search_budget=96)
        return choice,log
    # Preserve urgent/ongoing survival, crafting and protection. Social influence
    # only uses the baseline's optional rest/exploration window.
    if base is None or base['action']!='rest' or base['goal'] not in ('rest_survival','explore_local','rest_fatigue','reduce_exposure'):
        return alternate,log
    if max(body['hunger'],body['thirst'])>=.6 or env.get('cold_burden',0)>=.2 or body['health']<.9:
        return alternate,log
    visible={e['entity_id']:e for e in o['visible_entities'] if e['kind']=='actor'}
    near=[a for a,e in visible.items() if a!=s['owner'] and math.dist(o['own_state']['position_m'],e['position_m'])<=1.5]
    now=int(o['tick']);elapsed=(now-x['last_social'])*o['dt_s']
    # Gratitude is operationalized as feasible reciprocation, never a sentence
    # counted as helpful behavior. Own food/water reserve must remain protected.
    if elapsed>=30:
        targets=[dict(action='gratitude',target=a) for a in sorted(near)]
        gratitude=social.influence(x['social'],targets) if targets else None
        if gratitude:
            for material in ('water','food'):
                if int(o['own_state']['inventory_ug'].get(material,0))>=100000000:
                    trace['social']=gratitude
                    choice=policy.option('give',dict(material=material,mass_kg=.01),gratitude['target'],1,'reciprocate_observed_help')
                    log.update(changed=True,origin='acquired gratitude prerequisites + authored safe reciprocation')
                    return choice,log
    heard=[r for r in o['audible_reports'] if r['speaker_id'] in near and r['text'].startswith('sig-')]
    if heard and elapsed>=30:
        message=max(heard,key=lambda r:int(r['source_event_seq']))
        interpreted=communication._interpret(x['communication'],message['speaker_id'],message['text'])
        trace['communication']=interpreted
        if interpreted['meaning']=='distress' and interpreted['confidence']>=.5:
            ranking=relations.choose_helper(x['relationships'],near)
            target=ranking['other'] if ranking else message['speaker_id'];trace['relationship']=ranking
            hypotheses=x['inferences'].get(target,{}).get('estimates',{}).get('needs',{})
            trace['inference']=deepcopy(hypotheses)
            material=max(('food','water'),key=lambda k:hypotheses.get(k,{}).get('belief',0))
            if int(o['own_state']['inventory_ug'].get(material,0))>=100000000:
                log.update(changed=True,origin='learned signal + directional helper choice + public needs hypothesis; authored transfer')
                return policy.option('give',dict(material=material,mass_kg=.01),target,1,'assist_acquired_signal'),log
    # Learn whether time-costed rest helps in this context. Candidate durations
    # are native feasible; efficacy, not an emotional label, selects the duration.
    candidates=[dict(strategy='rest',action_type='rest',parameters={'seconds':d},
                     requested_duration=d,estimated_cost_s=d) for d in (1,5)]
    regulated=regulation.choose(o,x['regulation'],candidates)
    trace['regulation']=regulated
    value_choice=values.choose_commitment_action(x['values'],dict(owner=s['owner'],run_id=s['run_id']),
        [dict(action='rest',value='recovery',feasible=True,context=[memory.affect.cue(o)])])
    trace['values']=value_choice
    if value_choice and body['fatigue']>.25:
        log.update(changed=True,origin='acquired recovery preference + authored feasible rest')
        return policy.option(duration=regulated['requested_duration'],goal='acquired_recovery'),log
    # Native speech is the sole delivery channel. Emission meanings stay private;
    # listeners acquire independent associations from their own observations.
    if visible and (now-x['last_signal'])*o['dt_s']>=30 and body['fatigue']<.75:
        meaning=_meaning(o)
        partners=sorted(a for a,e in visible.items() if a!=s['owner'] and math.dist(o['own_state']['position_m'],e['position_m'])<=o['hearing_range_m'])
        if meaning and partners:
            # Pure preview: authoritative production is committed in action hook.
            preview=deepcopy(x['communication'])
            sent=communication.emit(preview,meaning,partners[0],'preview:'+str(now))
            trace['communication']=dict(meaning=meaning,token=sent['token'],partner=partners[0],provenance='own bodily context')
            log.update(changed=True,origin='private coined symbol + authored native speech')
            return policy.option('speak',dict(text=sent['token']),duration=1,goal='express_own_context'),log
    return alternate,log
