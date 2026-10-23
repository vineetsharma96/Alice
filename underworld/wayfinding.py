"""H4 opt-in, native-grounded location reports and bounded need-based decisions."""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path

from . import community, developmental as dev, planning, storage, symbols
from .lease import Lease

LIMITS = {'sites': 2, 'location_channels': 2, 'outcomes': 8, 'sources': 16}
NEEDS = ('hunger', 'thirst')


def module_hash():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def cell(position):
    # Authored finite spatial abstraction; no symbol meanings or coordinates shared.
    return dev.digest([math.floor(float(v) / 8) for v in position])[:12]


def _person(db, agent):
    state = community._contract(db, agent)
    contract = dev._read(db, 'development_records', 'wayfinding-contract-' + agent, 'id')
    if contract['module_sha256'] != module_hash() or contract['agent'] != agent or contract['run_id'] != state['run_id']:
        raise ValueError('H4 mechanism/identity mismatch; original runtime required')
    if {e['token'] for e in state['production'].values()} & set(state['h4']['site_production'].values()):
        raise ValueError('resource and location token collision; explicit new experiment required')
    path = Path(db.execute('PRAGMA database_list').fetchone()[2])
    for key, site in state['h4']['sites'].items():
        proof = dev._read(db, 'development_records', site['evidence'], 'id')
        own = proof['observation']['own_state']['position_m']
        if proof['agent'] != agent or cell(own) != key or list(own) != list(site['position']):
            raise ValueError('own landmark position evidence mismatch')
    for key, token in state['h4']['site_production'].items():
        proof = dev._read(db, 'development_records', f'h4-production-{agent}-{key}', 'id')
        if proof['agent'] != agent or proof['cell'] != key or proof['token'] != token:
            raise ValueError('private location production evidence mismatch')
    for channel, meanings in state['h4']['location_comprehension'].items():
        for key, entry in meanings.items():
            if not entry['evidence'] or len(entry['evidence']) != min(16, entry['n']):
                raise ValueError('location proof counts missing')
            for ident in entry['evidence']:
                proof = dev._read(db, 'development_records', ident, 'id')
                if (proof['agent'] != agent or proof['cell'] != key or
                        proof['message']['speaker_id'] + ':' + proof['message']['text'] != channel):
                    raise ValueError('location proof meaning mismatch')
                if dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
                    raise ValueError('location native evidence missing')
    for entry in state['h4']['outcomes'].values():
        if not entry['evidence'] or len(entry['evidence']) != min(16, entry['n']):
            raise ValueError('need prediction proof counts missing')
        for ident in entry['evidence']:
            proof = dev._read(db, 'development_records', ident, 'id')
            if proof['agent'] != agent or any(proof[k] != entry[k] for k in ('kind', 'need', 'action')):
                raise ValueError('need prediction evidence mismatch')
            if dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
                raise ValueError('need prediction native evidence missing')
    return state


def _save_record(db, state, kind, payload, ident=None):
    state['version'] += 1
    ident = ident or f'h4-{kind}-{state["agent"]}-{state["version"]}'
    payload = dict(payload, agent=state['agent'], run_id=state['run_id'])
    dev._record(db, ident, state['agent'], 'h4_' + kind, payload)
    dev._put(db, 'development_people', state['agent'], state)
    return dict(json.loads(dev.dumps(payload)), record_id=ident)


def initialize(path, seed=43):
    community.initialize(path, seed)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent, in db.execute('SELECT agent FROM development_people').fetchall():
            state = community._contract(db, agent)
            state['h4'] = {'sites': {}, 'site_production': {}, 'location_comprehension': {},
                           'outcomes': {}, 'sources': {}, 'last_sighting': None,
                           'policy_decisions': 0, 'protective_fallbacks': 0}
            dev._put(db, 'development_people', agent, state)
            dev._record(db, 'wayfinding-contract-' + agent, agent, 'h4_contract', {
                'agent': agent, 'run_id': state['run_id'], 'module_sha256': module_hash(),
                'limits': LIMITS, 'spatial_prior': '8m categorical cells; own visited coordinates only',
                'motor_prior': 'authored routing, gather/consume prerequisites and one-site search cap',
                'goal_prior': 'own need >=.45 weighted by learned native relief; bounded inspection otherwise',
                'communication': 'one token per assigned context; no shared dictionary or sequences'})
        db.commit()
    return audit(path)


def private(path, agent, principal):
    if agent != principal:
        raise ValueError('private wayfinding access denied')
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        return _person(db, agent)['h4']


def _proof(db, path, message):
    events = dev._source_events(db, path, [message['source_event_seq']])
    event = events[message['source_event_seq']]
    if (event['type'], event['agent_id'], event['detail']) != ('speech', message['speaker_id'], message['text']):
        raise ValueError('H4 speech proof mismatch')
    return events


def remember_site(path, agent):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, head = storage._head(db)
        observation = world.observe_batch([agent])[0]
        state = _person(db, agent)
        key = cell(observation['own_state']['position_m'])
        sites = state['h4']['sites']
        if key not in sites:
            if len(sites) >= LIMITS['sites']:
                raise ValueError('visited landmark quota reached')
            ident = f'h4-site-{agent}-{key}'
            sites[key] = {'position': observation['own_state']['position_m'], 'evidence': ident}
            result = _save_record(db, state, 'site', {'cell': key, 'observation': observation, 'head': head}, ident)
        else:
            result = {'cell': key, **sites[key]}
        db.commit()
    return result


def coin_site(path, agent):
    remember_site(path, agent)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        observation = world.observe_batch([agent])[0]
        state = _person(db, agent)
        key = cell(observation['own_state']['position_m'])
        production = state['h4']['site_production']
        if key not in production:
            used = {e['token'] for e in state['production'].values()} | set(production.values())
            options = [t for t in symbols.ALPHABET if t not in used]
            if not options:
                raise ValueError('private alphabet exhausted')
            production[key] = options[dev.random_index(state, len(options))]
            _save_record(db, state, 'coin_site', {'cell': key, 'token': production[key],
                         'observation': observation, 'origin': 'private_seeded_coinage'},
                         f'h4-production-{agent}-{key}')
        db.commit()
    return production[key]


def learn_site(path, listener, speaker, after_seq=0, fault=None):
    """Ground in own current position and a nearby visible speaker, never a supplied site."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        observation = world.observe_batch([listener])[0]
        message = symbols._heard(observation, speaker, after_seq)
        state = _person(db, listener)
        if not message:
            raise ValueError('no new native location demonstration')
        ident = f'h4-ground-{listener}-{message["source_event_seq"]}'
        old = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=?', (ident, listener)).fetchone()
        if old:
            return dict(json.loads(old[0]), record_id=ident)
        own = observation['own_state']['position_m']
        seen = next((e for e in observation['visible_entities'] if e['entity_id'] == speaker), None)
        key = cell(own)
        if (not seen or math.dist(own, seen['position_m']) > 1.5 or cell(seen['position_m']) != key
                or int(observation['tick']) - int(message['delivery_tick']) > 2):
            raise ValueError('location grounding requires fresh co-located native observation')
        if key not in state['h4']['sites']:
            raise ValueError('remember your actually visited landmark before grounding')
        channel = speaker + ':' + message['text']
        vocabulary = state['h4']['location_comprehension']
        if channel not in vocabulary and len(vocabulary) >= LIMITS['location_channels']:
            raise ValueError('private location-channel quota reached')
        entry = vocabulary.setdefault(channel, {}).setdefault(key, {'n': 0, 'evidence': []})
        entry['n'] += 1
        entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        result = _save_record(db, state, 'location_grounding', {
            'cell': key, 'message': message, 'observation': observation,
            'native_events': _proof(db, path, message), 'origin': 'authored co-visit demonstration'}, ident)
        if fault:
            fault('before_commit')
        db.commit()
        if fault:
            fault('after_commit')
        return result


def memory_hash(state):
    return dev.digest({'resource': symbols.vocabulary_hash(state),
        'site_production': state['h4']['site_production'],
        'location_comprehension': state['h4']['location_comprehension'],
        'outcomes': state['h4']['outcomes']})


def receive(path, listener, speaker, after_seq=0):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, _ = storage._head(db)
        observation = world.observe_batch([listener])[0]
        state = _person(db, listener)
        message = symbols._heard(observation, speaker, after_seq)
        if not message:
            return {'location': None, 'verified': False, 'reason': 'no_new_delivered_signal', 'record_id': None}
        ident = f'h4-report-{listener}-{message["source_event_seq"]}'
        old = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=?', (ident, listener)).fetchone()
        if old:
            return dict(json.loads(old[0]), record_id=ident)
        association = state['h4']['location_comprehension'].get(speaker + ':' + message['text'], {})
        scores = {key: e['n'] for key, e in association.items() if key in state['h4']['sites']}
        best = max(scores.values(), default=0)
        options = [k for k, score in scores.items() if score == best]
        key = options[0] if best and len(options) == 1 else None
        result = _save_record(db, state, 'report', {'location': key, 'verified': False,
            'reason': 'learned_location_report' if key else 'unknown_location_or_identity_only',
            'message': message, 'observation': observation, 'native_events': _proof(db, path, message)}, ident)
        db.commit()
        return result


def walk(path, agent, destination):
    """Authored bounded routing over own current perception; all movement is native."""
    records = []
    for _ in range(96):
        observation = dev.own_observation(path, agent)
        if math.dist(observation['own_state']['position_m'], destination) < .05:
            return records
        point = planning._route(observation, destination)
        if not point:
            raise ValueError('own-observation route unavailable')
        duration = min(60, max(1, math.ceil(math.dist(observation['own_state']['position_m'], point))))
        result = dev.execute(path, agent, 'move', parameters={'x_m': point[0], 'y_m': point[1]}, duration=duration, update_memory=False)
        records.append(result)
        if result['receipt']['status'] != 'completed':
            raise ValueError('native route failure: ' + result['receipt']['error_code'])
    raise ValueError('navigation step quota reached')


def observe_source(path, agent, material='water'):
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        world, _, _, head = storage._head(db)
        observation = world.observe_batch([agent])[0]
        state = _person(db, agent)
        own = observation['own_state']['position_m']
        choices = [e for e in observation['visible_entities'] if e['kind'] == material and
                   int(e['mass_ug']) >= 50000000 and math.dist(own, e['position_m']) <= 1.5]
        if not choices:
            return None
        entity = sorted(choices, key=lambda e: e['entity_id'])[0]
        sources = state['h4']['sources']
        if entity['entity_id'] not in sources and len(sources) >= LIMITS['sources']:
            raise ValueError('own source memory quota reached')
        memory = {'entity_id': entity['entity_id'], 'kind': entity['kind'], 'position': entity['position_m'],
                  'mass_ug': entity['mass_ug'], 'cell': cell(own), 'feature': symbols.percept(entity)}
        record = _save_record(db, state, 'sighting', {'source': memory, 'observation': observation, 'head': head})
        memory['evidence'] = record['record_id']
        sources[entity['entity_id']] = memory
        state['h4']['last_sighting'] = memory
        dev._put(db, 'development_people', agent, state)
        db.commit()
        return memory


def send(path, scout, mode='enabled'):
    if mode not in ('enabled', 'muted', 'scrambled', 'identity'):
        raise ValueError('unknown H4 communication arm')
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        state = _person(db, scout)
        sighting = state['h4']['last_sighting']
        if not sighting:
            raise ValueError('scout has no actual prior resource sighting')
        proof = dev._read(db, 'development_records', sighting['evidence'], 'id')
        if proof['source']['entity_id'] != sighting['entity_id']:
            raise ValueError('scout sighting provenance mismatch')
        production = state['h4']['site_production']
        token = production.get(sighting['cell'])
        if mode == 'scrambled':
            token = next((t for key, t in production.items() if key != sighting['cell']), None)
        if mode == 'identity':
            token = state['production'].get(sighting['feature'], {}).get('token')
        if mode != 'muted' and not token:
            raise ValueError('missing own learned production for this report')
    return dev.execute(path, scout, 'rest' if mode == 'muted' else 'speak',
                       parameters={} if mode == 'muted' else {'text': token}, update_memory=False)


def _experience(db, agent, ident):
    row = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=? AND kind=?',
                     (ident, agent, 'experience')).fetchone()
    if not row:
        raise ValueError('missing own native outcome experience')
    return json.loads(row[0])


def learn_relief(path, agent, gather_id, consume_id, fault=None):
    """Exactly-once update from actual acquired material and measured own need change."""
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        ident = 'h4-outcome-' + consume_id
        old = db.execute('SELECT payload FROM development_records WHERE id=? AND agent=?', (ident, agent)).fetchone()
        if old:
            previous = json.loads(old[0])
            if previous['gather_id'] != gather_id:
                raise ValueError('conflicting outcome acquisition identity')
            return dict(previous, record_id=ident)
        gathered = _experience(db, agent, gather_id)
        consumed = _experience(db, agent, consume_id)
        if gathered['receipt']['status'] != 'completed' or consumed['receipt']['status'] != 'completed':
            raise ValueError('uncompleted actions cannot teach a successful relief prediction')
        if gathered['request']['action_type'] != 'gather' or consumed['request']['action_type'] not in ('eat', 'drink'):
            raise ValueError('relief learning requires gather then native consumption')
        target = gathered['request']['target_ids'][0]
        entity = next(e for e in gathered['before']['visible_entities'] if e['entity_id'] == target)
        gain = int(gathered['after']['own_state']['inventory_ug'].get(entity['kind'], 0)) - int(gathered['before']['own_state']['inventory_ug'].get(entity['kind'], 0))
        ingested = int(consumed['receipt']['observable_effects'].get('description', '').split('=')[-1]) if '=' in consumed['receipt']['observable_effects'].get('description', '') else 0
        if gain <= 0 or ingested <= 0 or int(gathered['after']['tick']) > int(consumed['before']['tick']):
            raise ValueError('native acquisition/consumption ordering proof missing')
        changes = {need: consumed['before']['own_state']['body'][need] - consumed['after']['own_state']['body'][need] for need in NEEDS}
        need = max(changes, key=changes.get)
        action = consumed['request']['action_type']
        material = 'water' if action == 'drink' else consumed['request']['parameters'].get('material', 'food')
        if entity['kind'] != material or changes[need] <= 0:
            raise ValueError('acquired material did not cause observable need relief')
        key = dev.digest([entity['kind'], action, need])[:16]
        outcomes = state['h4']['outcomes']
        if key not in outcomes and len(outcomes) >= LIMITS['outcomes']:
            raise ValueError('need prediction quota reached')
        entry = outcomes.setdefault(key, {'kind': entity['kind'], 'action': action, 'need': need, 'n': 0, 'relief_sum': 0., 'evidence': []})
        entry['n'] += 1
        entry['relief_sum'] += changes[need]
        entry['evidence'] = (entry['evidence'] + [ident])[-16:]
        events = dict(gathered['native_events'], **consumed['native_events'])
        result = _save_record(db, state, 'outcome', {'gather_id': gather_id, 'consume_id': consume_id,
            'kind': entity['kind'], 'action': action, 'need': need, 'relief': changes[need], 'native_events': events}, ident)
        if fault:
            fault('before_commit')
        db.commit()
        if fault:
            fault('after_commit')
        return result


def choose_goal(path, agent, frozen=False):
    """No assigned goal, global source, target or other person's state input."""
    observation = dev.own_observation(path, agent)
    state = private(path, agent, agent)
    predictions = []
    if not frozen:
        for entry in state['outcomes'].values():
            need = observation['own_state']['body'][entry['need']]
            mean = entry['relief_sum'] / entry['n']
            if need >= .45 and mean > 0:
                predictions.append({'kind': entry['kind'], 'action': entry['action'], 'need': entry['need'],
                                    'score': need * mean, 'evidence': entry['evidence']})
    selected = max(predictions, key=lambda p: (p['score'], p['kind'])) if predictions else None
    return {'goal': selected, 'origin': 'own_needs_and_learned_native_relief' if selected else 'authored_bounded_inspection_or_information_inquiry',
            'needs': {need: observation['own_state']['body'][need] for need in NEEDS},
            'prediction_ablation': frozen, 'protective_fallback': False}


def acquire(path, agent, kind, action, report=None, assigned=True):
    """One-site authored execution; all coordinates and candidates come from own memory/sight."""
    start = dev.own_observation(path, agent)
    routes = []
    curiosity = False
    if report is not None:
        with Lease(path), closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent)
            if report.get('record_id'):
                proof = dev._read(db, 'development_records', report['record_id'], 'id')
                if proof['agent'] != agent or proof != {k: v for k, v in report.items() if k != 'record_id'}:
                    raise ValueError('supplied report does not match own native delivery record')
            elif report.get('location') is not None:
                raise ValueError('unproved location input is forbidden')
            sites = state['h4']['sites']
            key = report.get('location')
            if key not in sites:
                curiosity = True
                keys = sorted(sites)
                if not keys:
                    raise ValueError('no personally visited landmarks')
                key = keys[dev.random_index(state, len(keys))]
                dev._put(db, 'development_people', agent, state)
            destination = sites[key]['position']
            db.commit()
        routes = walk(path, agent, destination)
    observation = dev.own_observation(path, agent)
    visible = [e for e in observation['visible_entities'] if e['kind'] == kind and int(e['mass_ug']) >= 50000000
               and math.dist(observation['own_state']['position_m'], e['position_m']) <= 1.5]
    if not visible:
        return {'goal_completed': False, 'report_confirmed': False, 'reason': 'no_accessible_stock_at_attempted_site',
                'before': start, 'arrival': observation, 'route': routes, 'curiosity_fallback': curiosity,
                'assigned': assigned, 'protective_fallback': False, 'actions': []}
    target = sorted(visible, key=lambda e: e['entity_id'])[0]['entity_id']
    inspected = dev.execute(path, agent, 'inspect', [target], update_memory=False)
    fresh = dev.own_observation(path, agent)
    current = next((e for e in fresh['visible_entities'] if e['entity_id'] == target), None)
    if not current or int(current['mass_ug']) < 50000000:
        return {'goal_completed': False, 'report_confirmed': False, 'reason': 'stock_changed_after_inspection',
                'before': start, 'arrival': fresh, 'route': routes, 'curiosity_fallback': curiosity,
                'assigned': assigned, 'protective_fallback': False, 'actions': [inspected]}
    gathered = dev.execute(path, agent, 'gather', [target], {'mass_kg': .05}, update_memory=False)
    actions = [inspected, gathered]
    if gathered['receipt']['status'] == 'completed':
        actions.append(dev.execute(path, agent, action, parameters={'mass_kg': .05},
                                   duration=2 if action == 'eat' else 1, update_memory=False))
    gain = int(gathered['after']['own_state']['inventory_ug'].get(kind, 0)) - int(gathered['before']['own_state']['inventory_ug'].get(kind, 0))
    consumed = actions[-1] if len(actions) == 3 else None
    need = 'thirst' if action == 'drink' else 'hunger'
    relief = consumed['before']['own_state']['body'][need] - consumed['after']['own_state']['body'][need] if consumed else 0
    completed = (len(actions) == 3 and all(a['receipt']['status'] == 'completed' for a in actions)
                 and gain == 50000000 and consumed['receipt']['observable_effects'].get('description') == 'ingested_ug=50000000' and relief > 0)
    confirmed = bool(completed and report and report.get('location') == cell(observation['own_state']['position_m']))
    confirmation = None
    if confirmed:
        with Lease(path), closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE')
            state = _person(db, agent)
            events = {k: v for a in actions for k, v in a['native_events'].items()}
            confirmation = _save_record(db, state, 'confirmation', {
                'report_id': report['record_id'], 'source': target,
                'inspect_id': inspected['request']['request_id'], 'gather_id': gathered['request']['request_id'],
                'consume_id': consumed['request']['request_id'], 'native_events': events,
                'status': 'confirmed_by_own_native_acquisition_and_consumption'},
                'h4-confirm-' + consumed['request']['request_id'])
            db.commit()
    return {'goal_completed': completed, 'report_confirmed': confirmed, 'confirmation': confirmation,
            'reason': 'native_acquisition_and_consumption' if completed else 'native_failure',
            'before': start, 'arrival': observation, 'after': dev.own_observation(path, agent),
            'route': routes, 'actions': actions, 'source': target, 'curiosity_fallback': curiosity,
            'assigned': assigned, 'protective_fallback': False, 'acquired_ug': gain, 'need_relief': relief}


def policy_step(path, agent, frozen=False):
    decision = choose_goal(path, agent, frozen)
    with Lease(path), closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        state = _person(db, agent)
        state['h4']['policy_decisions'] += 1
        recorded = _save_record(db, state, 'goal_decision', {'decision': decision,
                                'origin': 'engineered scheduler; no assigned goal'})
        db.commit()
    decision['record_id'] = recorded['record_id']
    goal = decision['goal']
    if not goal:
        observation = dev.own_observation(path, agent)
        candidates = [e for e in observation['visible_entities'] if e['kind'] in ('food', 'water')
                      and math.dist(e['position_m'], observation['own_state']['position_m']) <= 1.5]
        action = dev.execute(path, agent, 'inspect' if candidates else 'rest',
                             [candidates[0]['entity_id']] if candidates else [], update_memory=False)
        return {'decision': decision, 'information_inquiries': 1, 'execution': None, 'inspection_or_rest': action}
    own = dev.own_observation(path, agent)
    if int(own['own_state']['inventory_ug'].get(goal['kind'], 0)) >= 50000000:
        # Resume from real carried supplies, including an interrupted gather.
        result = dev.execute(path, agent, goal['action'], parameters={'mass_kg': .05},
                             duration=2 if goal['action'] == 'eat' else 1, update_memory=False)
        relief = result['before']['own_state']['body'][goal['need']] - result['after']['own_state']['body'][goal['need']]
        return {'decision': decision, 'information_inquiries': 0,
                'execution': {'goal_completed': result['receipt']['status'] == 'completed' and relief > 0,
                              'actions': [result], 'used_carried': True, 'acquired_ug': 0,
                              'need_relief': relief, 'assigned': False, 'protective_fallback': False},
                'revisit_route': []}
    execution = acquire(path, agent, goal['kind'], goal['action'], assigned=False)
    revisit = []
    if not execution['goal_completed']:
        memories = private(path, agent, agent)['sources']
        candidates = [s for s in memories.values() if s['kind'] == goal['kind'] and int(s['mass_ug']) >= 50000000]
        if candidates:
            revisit = walk(path, agent, candidates[0]['position'])
            execution = acquire(path, agent, goal['kind'], goal['action'], assigned=False)
        else:
            observation = dev.own_observation(path, agent)
            heard = sorted(observation['audible_reports'], key=lambda r: int(r['source_event_seq']), reverse=True)
            if heard:
                report = receive(path, agent, heard[0]['speaker_id'])
                if report['location'] is not None:
                    execution = acquire(path, agent, goal['kind'], goal['action'], report, assigned=False)
                    return {'decision': decision, 'information_inquiries': 1, 'used_information': True,
                            'execution': execution, 'revisit_route': revisit}
            action = dev.execute(path, agent, 'rest', update_memory=False)
            return {'decision': decision, 'information_inquiries': 1, 'used_information': False,
                    'execution': execution, 'inquiry_rest': action, 'revisit_route': revisit}
    return {'decision': decision, 'information_inquiries': 0, 'used_information': False,
            'execution': execution, 'revisit_route': revisit}


def audit(path):
    result = community.audit(path)
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        for agent in result['people']:
            state = _person(db, agent)
            h4 = state['h4']
            for table, limit in (('sites', 2), ('site_production', 2), ('location_comprehension', 2), ('outcomes', 8), ('sources', 16)):
                if len(h4[table]) > limit:
                    raise ValueError('H4 private memory limit exceeded')
            for channel, meanings in h4['location_comprehension'].items():
                for key, entry in meanings.items():
                    for ident in entry['evidence']:
                        proof = dev._read(db, 'development_records', ident, 'id')
                        if proof['agent'] != agent or proof['cell'] != key or proof['message']['speaker_id'] + ':' + proof['message']['text'] != channel:
                            raise ValueError('location evidence meaning/owner mismatch')
            for entry in h4['outcomes'].values():
                for ident in entry['evidence']:
                    proof = dev._read(db, 'development_records', ident, 'id')
                    if proof['agent'] != agent or any(proof[k] != entry[k] for k in ('kind', 'need', 'action')):
                        raise ValueError('need prediction evidence mismatch')
        for kind, payload in db.execute("SELECT kind,payload FROM development_records WHERE kind LIKE 'h4_%'"):
            proof = json.loads(payload)
            if proof.get('native_events') and dev._source_events(db, path, list(proof['native_events'])) != proof['native_events']:
                raise ValueError('H4 native source missing')
    result['h4_memory_hashes'] = {a: memory_hash(s) for a, s in result['people'].items()}
    return result
