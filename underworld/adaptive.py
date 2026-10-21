"""Separately contracted H0-H5 gap study. All selection/motor priors are explicit."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re

from . import composition as comp, developmental as dev, planning, storage, symbols, wayfinding as wf
from .lease import Lease

LIMITS = dict(sites=3, sources=16, quality=16, ranges=128, reports=64, hypotheses=32)
REPORT_AGE = 60.0
SOURCE_AGE = 120.0


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _record(db, state, kind, payload, ident=None):
    state['version'] += 1
    ident = ident or f'gap-{kind}-{state["agent"]}-{state["version"]}'
    value = json.loads(dev.dumps(dict(payload, agent=state['agent'], run_id=state['run_id'])))
    dev._record(db, ident, state['agent'], 'gap_' + kind, value)
    dev._put(db, 'development_people', state['agent'], state)
    return dict(value, record_id=ident)


def _person(db, agent):
    state = comp._person(db, agent)
    contract = dev._read(db, 'development_records', 'gap-contract-' + agent, 'id')
    if (contract['module_sha256'], contract['agent'], contract['run_id'], contract['limits']) != (module_hash(), agent, state['run_id'], LIMITS):
        raise ValueError('gap source/identity contract mismatch')
    h = state['adaptive']
    for table in LIMITS:
        if len(h[table]) > LIMITS[table]:
            raise ValueError('gap private quota reached: ' + table)
    path = Path(db.execute('PRAGMA database_list').fetchone()[2])
    # Every prediction/coordinate must retain its own source, including after epochs.
    references = {e['evidence'] for e in h['ranges']}
    for table in ('quality', 'hypotheses'):
        for entry in h[table].values():
            references.update(entry['evidence'])
    for table in ('sites', 'sources', 'production'):
        references.update(e['evidence'] for e in h[table].values())
    for ident in references:
        proof = dev._read(db, 'development_records', ident, 'id')
        if proof['agent'] != agent or proof['run_id'] != state['run_id']:
            raise ValueError('gap private source owner mismatch')
        if 'native_events' in proof and dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
            raise ValueError('gap native source missing')
    for key, site in h['sites'].items():
        p=dev._read(db,'development_records',site['evidence'],'id')
        if wf.cell(p['observation']['own_state']['position_m'])!=key or list(p['observation']['own_state']['position_m'])!=site['position']:
            raise ValueError('unproved own coordinate')
    for source in h['sources'].values():
        p=dev._read(db,'development_records',source['evidence'],'id')
        entity=comp._entity(p['observation'],source['entity_id'])
        if p['source']!={k:v for k,v in source.items() if k!='evidence'} or source['position']!=list(entity['position_m']) or source['mass_ug']!=int(entity['mass_ug']):
            raise ValueError('own source memory mismatch')
    for channel,entry in h['hypotheses'].items():
        if len(entry['evidence'])!=min(16,entry['n']):raise ValueError('location count/source mismatch')
        for ident in entry['evidence']:
            p=dev._read(db,'development_records',ident,'id')
            if channel.split(':',1)[0]!=p['message']['speaker_id'] or channel.split(':',1)[1] not in comp.parse(p['message']['text']) or not set(entry['possible'])<=set(p['values']):
                raise ValueError('location association source mismatch')
            wf._proof(db,path,p['message'])
    return state


def attach(path, agents=None):
    """Explicitly extend compatible working lives, preserving every old private field."""
    comp.audit(path)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        available = [r[0] for r in db.execute('SELECT agent FROM development_people')]
        if db.execute('SELECT 1 FROM development_pending').fetchone():
            raise ValueError('finish native pending work before attaching a profile')
        selected = available if agents is None else list(agents)
        if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(available):
            raise ValueError('select existing distinct learners explicitly')
        for agent in selected:
            state = comp._person(db, agent)
            if 'adaptive' in state:
                raise ValueError('gap profile already attached; never reset a learner')
            state['adaptive'] = dict(sites={}, sources={}, quality={}, ranges=[], reports={},
                hypotheses={}, production={}, messages={}, attention=None, pending=None, plan=None,
                serial=0, goals=0, decisions=0, shared=[], reports_sent=0, external_teaching=0,
                protective_fallbacks=0, exploration=0)
            dev._record(db, 'gap-contract-' + agent, agent, 'gap_contract', dict(
                agent=agent, run_id=state['run_id'], module_sha256=module_hash(), limits=LIMITS,
                priors='distance monotonicity; category/cell factorization; engineered needs, routing and novelty sharing',
                native_reach_constant_supplied_to_learner=False))
            dev._put(db, 'development_people', agent, state)
        db.commit()
    return audit(path)


def initialize(path, seed=53):
    comp.initialize(path, seed)
    return attach(path)


def private(path, agent, principal):
    if agent != principal:
        raise ValueError('private adaptive access denied')
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        return _person(db, agent)['adaptive']


def perform(path, agent, logical_id, action, targets=(), parameters=None, duration=1, fault=None):
    """Generic exactly-once native primitive, also used by persisted multi-step plans."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,90}', logical_id):
        raise ValueError('invalid logical action identity')
    spec = dict(action=action, targets=list(targets), parameters=parameters or {}, duration=duration)
    ident = f'gap-action-{agent}-{logical_id}'
    with Lease(path):
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent)
            if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone():
                intent = dev._read(db, 'development_records', ident, 'id')
                if intent['spec'] != spec:
                    raise ValueError('conflicting logical action')
            else:
                if db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone():
                    raise ValueError('reconcile pending native action first')
                if db.execute('SELECT COUNT(*) FROM development_records WHERE agent=?', (agent,)).fetchone()[0] > dev.QUOTA - 4:
                    raise ValueError('gap quota before physical action')
                o = dev.own_observation(path, agent)
                intent = dict(spec=spec, request_id=f'dev-{agent}-{state["counter"] + 1}', observation_version=o['observation_version'])
                _record(db, state, 'intent', intent, ident)
            db.commit()
        if fault:
            fault('after_logical_intent')
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute('BEGIN')
            found = db.execute('SELECT 1 FROM development_records WHERE id=?', (intent['request_id'],)).fetchone()
            pending = db.execute('SELECT 1 FROM development_pending WHERE agent=?', (agent,)).fetchone()
            if found:
                experience = dev._read(db, 'development_records', intent['request_id'], 'id')
            elif pending:
                p = dev._read(db, 'development_pending', agent, 'agent')
                if p['request']['request_id'] != intent['request_id']:
                    raise ValueError('gap pending request mismatch')
            elif dev.own_observation(path, agent)['observation_version'] != intent['observation_version'] or f'dev-{agent}-{_person(db, agent)["counter"] + 1}' != intent['request_id']:
                raise ValueError('unsubmitted gap intent at changed head')
        if not found:
            experience = (dev.reconcile(path, agent, fault=fault) if pending else
                dev.execute(path, agent, action, targets, parameters, duration,
                            prediction={'gap_logical_id': ident}, fault=fault, update_memory=False))
        r = experience['request']
        if (r['action_type'], r['target_ids'], r['parameters'], r['requested_duration']) != (action, list(targets), parameters or {}, duration):
            raise ValueError('logical/native request conflict')
        return json.loads(dev.dumps(experience))


def learn_outcome(path, agent, request_id):
    ident = 'gap-online-' + request_id
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone():
            return dict(dev._read(db, 'development_records', ident, 'id'), record_id=ident)
        e = wf._experience(db, agent, request_id)
        if e['request']['action_type'] != 'gather':
            raise ValueError('online learner requires own gather evidence')
        target = next((x for x in e['before']['visible_entities'] if x['entity_id'] in e['request']['target_ids']), None)
        h = state['adaptive']
        error = e['receipt']['error_code'] or e['receipt']['status']
        category = dev.digest(target['kind'])[:12] if target else None
        gain = e['food_gain_ug'] > 0
        distance = math.dist(target['position_m'], e['before']['own_state']['position_m']) if target else None
        if target and (e['receipt']['status'] == 'completed' or error == 'OUT_OF_REACH'):
            if len(h['ranges']) >= LIMITS['ranges']:
                raise ValueError('range observation quota reached')
            h['ranges'].append(dict(distance=distance, reachable=error != 'OUT_OF_REACH', evidence=ident))
        if target and e['receipt']['status'] == 'completed':
            if category not in h['quality'] and len(h['quality']) >= 16:
                raise ValueError('quality context quota reached')
            entry = h['quality'].setdefault(category, dict(n=0, successes=0, evidence=[]))
            entry['n'] += 1
            entry['successes'] += gain
            entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        result = _record(db, state, 'online', dict(request_id=request_id, category=category,
            distance=distance, food_gain=gain, native_outcome=error, native_events=e['native_events'],
            origin='native terminal result; reach failures do not label food quality'), ident)
        db.commit()
        return result


def predict(state, entity, own, mode='learning'):
    h = state['adaptive']
    distance = math.dist(entity['position_m'], own['position_m'])
    quality = h['quality'].get(dev.digest(entity['kind'])[:12], dict(n=0, successes=0))
    if mode == 'frozen':
        return dict(probability=.5, quality=.5, reach=.5, uncertain=True)
    successes = [r for r in h['ranges'] if r['reachable'] and distance <= r['distance'] + 1e-9]
    failures = [r for r in h['ranges'] if not r['reachable'] and distance >= r['distance'] - 1e-9]
    reach = (len(successes) + 1) / (len(successes) + len(failures) + 2)
    q = (quality['successes'] + 1) / (quality['n'] + 2)
    return dict(probability=reach*q, quality=q, reach=reach, uncertain=not successes and not failures)


def choose(path, agent, candidates, mode='learning'):
    if mode not in ('learning', 'frozen'):
        raise ValueError('unknown gap comparator')
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        o = dev.own_observation(path, agent)
        options = []
        for entity in o['visible_entities']:
            if entity['entity_id'] in candidates and int(entity['mass_ug']) >= 1000000:
                options.append(dict(target=entity['entity_id'], **predict(state, entity, o['own_state'], mode)))
        best = max((x['probability'] for x in options), default=0)
        eligible = [x for x in options if x['probability'] == best]
        selected = eligible[dev.random_index(state, len(eligible))] if eligible and best >= .5 else None
        exploration = False
        if not selected and eligible and eligible[0]['uncertain'] and state['adaptive']['exploration'] < 3:
            selected = eligible[dev.random_index(state, len(eligible))]
            state['adaptive']['exploration'] += 1
            exploration = True
        dev._put(db, 'development_people', agent, state)
        db.commit()
        return dict(target=selected['target'] if selected else None, predictions=options,
                    authored_exploration=exploration, mode=mode, observation_version=o['observation_version'])


def refresh(path, agent, remember_site=False):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        o = dev.own_observation(path, agent)
        h = state['adaptive']
        key = wf.cell(o['own_state']['position_m'])
        if remember_site and key not in h['sites']:
            if len(h['sites']) >= 3:
                raise ValueError('own landmark budget reached')
            ident = f'gap-site-{agent}-{key}'
            h['sites'][key] = dict(position=list(o['own_state']['position_m']), evidence=ident)
            _record(db, state, 'site', dict(cell=key, observation=o), ident)
        for entity in o['visible_entities']:
            if entity['kind'] not in ('food', 'water'):
                continue
            old = h['sources'].get(entity['entity_id'])
            if old and old['mass_ug'] == int(entity['mass_ug']) and (int(o['tick']) - old['tick'])*o['dt_s'] < 30:
                continue
            if not old and len(h['sources']) >= 16:
                raise ValueError('own source budget reached')
            memory = dict(entity_id=entity['entity_id'], kind=entity['kind'], position=list(entity['position_m']),
                mass_ug=int(entity['mass_ug']), tick=int(o['tick']), cell=wf.cell(entity['position_m']),
                depleted=int(entity['mass_ug']) < 50000000)
            proof = _record(db, state, 'source', dict(source=memory, observation=o))
            memory['evidence'] = proof['record_id']
            h['sources'][entity['entity_id']] = memory
        dev._put(db, 'development_people', agent, state)
        db.commit()
    return key


def _location_features(entity, position):
    return ['kind:' + dev.digest(entity['kind'])[:12], 'site:' + wf.cell(position)]


def encode_location(path, agent, source_id, learn=False):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        h = state['adaptive']
        source = h['sources'].get(source_id)
        if not source or source['cell'] not in h['sites']:
            raise ValueError('own observed source and personally visited site required')
        values = ['kind:' + dev.digest(source['kind'])[:12], 'site:' + source['cell']]
        for value in values:
            if value not in h['production']:
                if not learn:
                    raise ValueError('unknown frozen location factor')
                used = ({e['token'] for e in state['h5']['production'].values()} |
                        {e['token'] for e in state['production'].values()} |
                        set(state['h4']['site_production'].values()) |
                        {e['token'] for e in h['production'].values()})
                options = [t for t in symbols.ALPHABET if t not in used]
                if not options:
                    raise ValueError('private alphabet exhausted')
                token = options[dev.random_index(state, len(options))]
                ident = f'gap-coin-{agent}-{state["version"] + 1}'
                h['production'][value] = dict(token=token, evidence=ident)
                _record(db, state, 'coin', dict(feature=value, token=token, source_evidence=source['evidence']), ident)
        tokens = [h['production'][v]['token'] for v in values]
        if dev.random_index(state, 2):
            tokens.reverse()
        dev._put(db, 'development_people', agent, state)
        db.commit()
        return ' '.join(tokens)


def begin_location(path, listener, ident, candidates):
    refresh(path, listener, remember_site=True)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, listener)
        if state['adaptive']['attention']:
            raise ValueError('finish pending location attention')
        o = dev.own_observation(path, listener)
        for target in candidates:
            comp._entity(o, target)
        state['adaptive']['attention'] = dict(id=ident, candidates=list(candidates), before=o,
            after_seq=max((int(r['source_event_seq']) for r in o['audible_reports']), default=0))
        dev._put(db, 'development_people', listener, state)
        db.commit()


def learn_location(path, listener, speaker, attention_id):
    ident = f'gap-location-{listener}-{attention_id}'
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, listener)
        if db.execute('SELECT 1 FROM development_records WHERE id=?', (ident,)).fetchone():
            proof = dev._read(db, 'development_records', ident, 'id')
            if proof['message']['speaker_id'] != speaker:
                raise ValueError('conflicting location learning identity')
            return dict(proof, record_id=ident)
        h = state['adaptive']
        a = h['attention']
        if not a or a['id'] != attention_id:
            raise ValueError('own location attention required')
        o = dev.own_observation(path, listener)
        if wf.cell(o['own_state']['position_m']) != wf.cell(a['before']['own_state']['position_m']):
            raise ValueError('location grounding moved during attention')
        changed = [t for t in a['candidates'] if int(comp._entity(o,t)['mass_ug']) != int(comp._entity(a['before'],t)['mass_ug'])]
        if len(changed) != 1 or int(comp._entity(o,changed[0])['mass_ug']) - int(comp._entity(a['before'],changed[0])['mass_ug']) != 1000000:
            raise ValueError('location grounding requires one native deposit')
        message = comp._heard(o, speaker, a['after_seq'])
        events = wf._proof(db, path, message)
        values = _location_features(comp._entity(a['before'], changed[0]), o['own_state']['position_m'])
        tokens = comp.parse(message['text'])
        for token in tokens:
            entry = h['hypotheses'].setdefault(speaker + ':' + token, dict(possible=values, n=0, evidence=[]))
            entry['possible'] = sorted(set(entry['possible']) & set(values))
            entry['n'] += 1
            entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        h['messages'][dev.dumps([speaker, sorted(tokens), values])] = ident
        h['external_teaching'] += 1
        h['attention'] = None
        proof = _record(db, state, 'location', dict(before=a['before'], after=o, candidates=a['candidates'],
            values=values, message=message, native_events=events), ident)
        db.commit()
        return proof


def receive(path, agent, kind, mode='learned'):
    if mode not in ('learned', 'whole', 'muted'):
        raise ValueError('unknown location receiver mode')
    if mode == 'muted':
        return None
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        h = state['adaptive']
        o = dev.own_observation(path, agent)
        reports = sorted(o['audible_reports'], key=lambda r:int(r['source_event_seq']), reverse=True)
        for message in reports:
            seq = message['source_event_seq']
            if seq in h['reports'] or (int(o['tick']) - int(message['delivery_tick']))*o['dt_s'] > REPORT_AGE:
                continue
            try:
                tokens = comp.parse(message['text'])
            except ValueError:
                continue
            if any(message['speaker_id'] + ':' + t not in h['hypotheses'] for t in tokens):
                continue
            scores = {}
            for site in h['sites']:
                values = ['kind:' + dev.digest(kind)[:12], 'site:' + site]
                if mode == 'whole':
                    score = int(dev.dumps([message['speaker_id'], sorted(tokens), values]) in h['messages'])
                else:
                    possible=[h['hypotheses'][message['speaker_id'] + ':' + t]['possible'] for t in tokens]
                    score = (sum(len(set(values) & set(p))/max(1,len(p)) for p in possible)
                             if all(set(values)&set(p) for p in possible) else 0)
                scores[site] = score
            best = max(scores.values(), default=0)
            sites = [s for s,v in scores.items() if v == best]
            if best <= 0 or len(sites) != 1:
                continue
            if len(h['reports']) >= 64:
                raise ValueError('report attempt budget reached')
            report = _record(db, state, 'report', dict(site=sites[0], kind=kind, scores=scores,
                message=message, native_events=wf._proof(db,path,message), verified=False))
            h['reports'][seq] = dict(record_id=report['record_id'], attempted=False)
            dev._put(db,'development_people',agent,state)
            db.commit()
            return report
        db.commit()
        return None


def share_step(path, agent):
    """Authored novelty-and-visible-peer rule; no operator target/recipient argument."""
    refresh(path, agent)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db,agent)
        h = state['adaptive']
        o = dev.own_observation(path,agent)
        peers = [e for e in o['visible_entities'] if e['kind']=='actor' and
                 math.dist(e['position_m'],o['own_state']['position_m']) <= o['hearing_range_m']]
        sources = [s for s in h['sources'].values() if not s['depleted'] and s['entity_id'] not in h['shared'] and
                   (int(o['tick'])-s['tick'])*o['dt_s'] <= SOURCE_AGE]
        sources.sort(key=lambda s:(-s['tick'],s['entity_id']))
        source = next((s for s in sources if all(f in h['production'] for f in
            ['kind:'+dev.digest(s['kind'])[:12],'site:'+s['cell']])),None)
        existing=h.get('share_pending')
        if (not peers or not source) and not existing:
            return dict(spoke=False,reason='no eligible new information or local peer')
        serial=h['serial']+1
        # Reserve the choice before native sending. Generic perform protects the utterance.
        ident=f'share-{serial}'
        if existing:
            source=h['sources'][existing['source']];ident=existing['id'];text=existing['text']
        else:
            h['serial']=serial
            text=' '.join(h['production'][f]['token'] for f in ['kind:'+dev.digest(source['kind'])[:12],'site:'+source['cell']])
            if dev.random_index(state,2):text=' '.join(reversed(text.split()))
            h['share_pending']=dict(id=ident,source=source['entity_id'],text=text)
        dev._put(db,'development_people',agent,state);db.commit()
    e=perform(path,agent,ident,'speak',parameters={'text':text},duration=len(comp.parse(text)))
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE');state=_person(db,agent);h=state['adaptive']
        if e['receipt']['status']=='completed':
            h['shared'].append(source['entity_id']);h['reports_sent']+=1
        h.pop('share_pending',None)
        result=_record(db,state,'sharing',dict(source_id=source['entity_id'],experience_id=e['request']['request_id'],
            native_events=e['native_events'],origin='authored novelty/peer selection; no assigned speech target'))
        db.commit()
    return dict(spoke=e['receipt']['status']=='completed',record=result,experience=e)


def _approach(o, destination):
    # Authored motor affordance, deliberately separate from learned reach prediction.
    if math.dist(o['own_state']['position_m'],destination)<=1.2:
        return None
    points=[(destination[0]+.9*math.cos(i*math.tau/8),destination[1]+.9*math.sin(i*math.tau/8)) for i in range(8)]
    points.sort(key=lambda p:math.dist(o['own_state']['position_m'],p))
    for p in points:
        if not .3<=p[0]<=o['world_bounds_m']['width']-.3 or not .3<=p[1]<=o['world_bounds_m']['height']-.3:
            continue
        if any(e['radius_m']>0 and math.dist(e['position_m'],p)<e['radius_m']+.3 for e in o['visible_entities']):
            continue
        route=planning._route(o,p)
        if route:
            return route
    raise ValueError('own observed approach blocked')


def step(path, agent, mode='learned', fault=None, cycle_id=None):
    """One durable frame; no assigned target or goal, never reads another private state."""
    with Lease(path):
        cycle_record=None
        if cycle_id is not None:
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',cycle_id):raise ValueError('invalid scheduler cycle identity')
            cycle_record=f'gap-cycle-{agent}-{cycle_id}'
            with closing(storage._connect(path,readonly=True)) as db:
                _person(db,agent)
                if db.execute('SELECT 1 FROM development_records WHERE id=?',(cycle_record,)).fetchone():
                    r=dev._read(db,'development_records',cycle_record,'id')
                    return dict(result=dict(r,record_id=cycle_record),experience=wf._experience(db,agent,r['experience_id']),goal_completed=r['goal_completed'],role=r['role'])
        h=private(path,agent,agent)
        if h['pending'] and h['pending'].get('cycle_id')!=cycle_id:raise ValueError('resume original scheduler cycle first')
        if not h['pending']:
            refresh(path,agent)
            goal=wf.choose_goal(path,agent)['goal']
            o=dev.own_observation(path,agent)
            if not h['plan'] and goal:
                h=private(path,agent,agent)
                sources=[s for s in h['sources'].values() if s['kind']==goal['kind'] and not s['depleted'] and
                         (int(o['tick'])-s['tick'])*o['dt_s']<=SOURCE_AGE]
                sources.sort(key=lambda s:math.dist(o['own_state']['position_m'],s['position']))
                report=None if sources else receive(path,agent,goal['kind'],mode)
                destination=sources[0]['position'] if sources else h['sites'][report['site']]['position'] if report else None
                carried=int(o['own_state']['inventory_ug'].get(goal['kind'],0))>=50000000
                if destination or carried:
                    with closing(storage._connect(path)) as db:
                        db.execute('BEGIN IMMEDIATE');state=_person(db,agent);x=state['adaptive']
                        x['serial']+=1
                        x['plan']=dict(id=x['serial'],goal=goal,destination=destination,steps=0,
                            report=report,gather_id=None,phase='consume' if carried else 'approach')
                        if report:x['reports'][report['message']['source_event_seq']]['attempted']=True
                        _record(db,state,'plan',dict(plan=x['plan'],origin='own need and learned relief; authored execution'))
                        db.commit()
            h=private(path,agent,agent);plan=h['plan'];o=dev.own_observation(path,agent)
            action,targets,parameters,duration,role='rest',[],{},30,'idle'
            if plan:
                if plan['steps']>=96:
                    raise ValueError('plan action bound reached')
                goal=plan['goal']
                carried=int(o['own_state']['inventory_ug'].get(goal['kind'],0))>=50000000
                if carried:
                    action,parameters,duration,role=goal['action'],{'mass_kg':.05},2 if goal['action']=='eat' else 1,'consume'
                else:
                    try:point=_approach(o,plan['destination'])
                    except ValueError:point=False
                    if point:
                        action,parameters,duration,role='move',dict(x_m=point[0],y_m=point[1]),max(1,min(60,math.ceil(math.dist(o['own_state']['position_m'],point)))),'approach'
                    else:
                        choices=[e for e in o['visible_entities'] if e['kind']==goal['kind'] and int(e['mass_ug'])>=50000000 and math.dist(e['position_m'],o['own_state']['position_m'])<=1.2]
                        if choices and point is not False:
                            action,targets,parameters,duration,role='gather',[sorted(choices,key=lambda e:e['entity_id'])[0]['entity_id']],{'mass_kg':.05},1,'gather'
                        else:role='scarcity';duration=1
            with closing(storage._connect(path)) as db:
                db.execute('BEGIN IMMEDIATE');state=_person(db,agent);x=state['adaptive'];x['decisions']+=1
                pending=dict(id=f'frame-{x["decisions"]}',action=action,targets=targets,parameters=parameters,duration=duration,role=role,cycle_id=cycle_id)
                x['pending']=pending;dev._put(db,'development_people',agent,state);db.commit()
        h=private(path,agent,agent);p=h['pending']
        e=perform(path,agent,p['id'],p['action'],p['targets'],p['parameters'],p['duration'],fault)
        if fault:fault('after_plan_native')
        if p['role']=='gather':learn_outcome(path,agent,e['request']['request_id'])
        plan=private(path,agent,agent)['plan']
        completed=False
        if p['role']=='consume':
            need=plan['goal']['need'];relief=e['before']['own_state']['body'][need]-e['after']['own_state']['body'][need]
            completed=e['receipt']['status']=='completed' and relief>0 and e['receipt']['observable_effects'].get('description')=='ingested_ug=50000000'
            if completed and plan['gather_id']:wf.learn_relief(path,agent,plan['gather_id'],e['request']['request_id'])
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');state=_person(db,agent);x=state['adaptive']
            if x['plan']:
                x['plan']['steps']+=1
                if p['role']=='gather' and e['receipt']['status']=='completed':
                    x['plan']['gather_id']=e['request']['request_id'];x['plan']['phase']='consume'
                if completed or p['role']=='scarcity' or e['receipt']['status']!='completed':x['plan']=None
            if completed:x['goals']+=1
            x['pending']=None
            result=_record(db,state,'frame',dict(logical_id=p['id'],role=p['role'],experience_id=e['request']['request_id'],
                goal_completed=completed,native_events=e['native_events'],assigned=False,protective_fallback=False),cycle_record)
            db.commit()
        return dict(result=result,experience=e,goal_completed=completed,role=p['role'])


def cohort_step(path,fault=None):
    """Authored round-robin scheduler with persisted, replay-safe frame identities."""
    with Lease(path):
        with closing(storage._connect(path,readonly=True)) as db:
            agents=[a for a,raw in db.execute('SELECT agent,payload FROM development_people ORDER BY agent') if 'adaptive' in json.loads(raw)]
            owner=agents[0];n=_person(db,owner)['adaptive'].get('scheduler_cursor',0)
        agent=agents[n%len(agents)]
        result=step(path,agent,cycle_id=f'cohort-{n}')
        if fault:fault('after_scheduler_frame')
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');state=_person(db,owner)
            state['adaptive']['scheduler_cursor']=n+1
            dev._put(db,'development_people',owner,state);db.commit()
        return dict(agent=agent,cursor=n+1,frame=result)


def audit(path):
    result=comp.audit(path)
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN')
        for agent,state in result['people'].items():
            if 'adaptive' not in state:continue
            own=_person(db,agent)
            for ident,raw in db.execute("SELECT id,payload FROM development_records WHERE agent=? AND kind LIKE 'gap_%'",(agent,)):
                proof=json.loads(raw)
                if proof['agent']!=agent or proof['run_id']!=own['run_id']:raise ValueError('gap evidence identity mismatch')
                if 'native_events' in proof and dev._source_events(db,path,list(proof['native_events']))!=proof['native_events']:raise ValueError('gap evidence chain missing')
            for key,site in own['adaptive']['sites'].items():
                proof=dev._read(db,'development_records',site['evidence'],'id')
                if wf.cell(proof['observation']['own_state']['position_m'])!=key or list(proof['observation']['own_state']['position_m'])!=site['position']:raise ValueError('unproved own coordinate')
    return result
