"""Explicitly assigned native setup actions; never an autonomous-policy success."""
import math
from contextlib import closing

from . import weather_store as store


class JournalWorld:
    """Route assigned setup through the same transactional native journal as a run."""
    def __init__(self,path):self.path=path

    def _read(self,method,*args):
        with closing(store.connect(self.path)) as db:
            world,_,_=store.head(db)
            return getattr(world,method)(*args)

    def snapshot(self):return self._read('snapshot')
    def weather_snapshot(self):return self._read('weather_snapshot')
    def checkpoint(self):return self._read('checkpoint')
    def check_invariants(self):return self._read('check_invariants')
    def observe_batch(self,agents):return self._read('observe_batch',agents)
    def submit(self,request,principal):
        return store.commit(self.path,dict(kind='submit',request=request,principal=principal,origin='operator_assigned_setup'))
    def step(self,ticks):return store.commit(self.path,dict(kind='step',ticks=ticks,origin='operator_assigned_setup'))


def request(w, action, target=None, parameters=None, duration=1, agent='agent-1', ident=None):
    o = w.observe_batch([agent])[0]
    return dict(schema_version=1, run_id=o['run_id'], request_id=ident or f"w-{agent}-{w.snapshot()['last_event_seq']}-{action}",
                agent_id=agent, observation_version=o['tick'], action_type=action,
                target_ids=[target] if target else [], parameters=parameters or {}, requested_duration=duration)


def execute(w, action, target=None, parameters=None, duration=1, agent='agent-1', ident=None):
    r = request(w, action, target, parameters, duration, agent, ident)
    receipt = w.submit(r, agent)
    if receipt['status'] == 'accepted':
        w.step(math.ceil(duration / w.snapshot()['dt_s']))
        receipt = next(x for x in w.observe_batch([agent])[0]['recent_action_results'] if x['request_id'] == r['request_id'])
    return receipt


def move(w, position, agent='agent-1'):
    o = w.observe_batch([agent])[0]
    length = math.dist(position, o['own_state']['position_m'])
    duration = max(.25, math.ceil(length / o['dt_s']) * o['dt_s'])
    receipt = execute(w, 'move', parameters=dict(x_m=position[0], y_m=position[1]), duration=duration, agent=agent)
    if receipt['status'] != 'completed':
        raise ValueError('Assigned setup move failed: ' + str(receipt))
    return receipt


def walk(w, position, agent='agent-1'):
    from underworld.planning import _route
    trace = []
    for _ in range(96):
        o = w.observe_batch([agent])[0]
        if math.dist(o['own_state']['position_m'], position) < .02:return trace
        point = _route(o, position)
        if point is None:raise ValueError('Assigned setup route blocked')
        trace.append(move(w, point, agent))
    raise ValueError('Assigned setup route budget')


def ingredients(w):
    trace = [move(w, [2, 28.8]), execute(w, 'harvest_branch', 'tree-1', dict(mass_kg=1))]
    trace += [move(w, [3.2, 28.9])]
    wood = next(e for e in w.observe_batch(['agent-1'])[0]['visible_entities'] if e['kind'] == 'wood')
    trace.append(execute(w, 'collect_wood', wood['entity_id'], dict(material='wood', mass_kg=.9)))
    trace += [move(w, [.8, 28.9])]
    fiber = next(e for e in w.observe_batch(['agent-1'])[0]['visible_entities'] if e['kind'] == 'fiber')
    trace.append(execute(w, 'collect_wood', fiber['entity_id'], dict(material='fiber', mass_kg=.1)))
    trace.append(move(w, [2.6, 4]))
    if any(r['status'] != 'completed' for r in trace):raise ValueError('Assigned ingredients failed: ' + str(trace))
    return trace


def site(w, position=(4, 4)):
    r = execute(w, 'begin_construction', parameters=dict(recipe_id='lean_to', x_m=position[0], y_m=position[1]))
    if r['status'] != 'completed':raise ValueError('Assigned site failed: ' + str(r))
    own = w.observe_batch(['agent-1'])[0]
    return next(e['entity_id'] for e in own['visible_entities'] if e['kind'] == 'construction' and e['recipe_id'] == 'lean_to')


def roof(w):
    trace = ingredients(w)
    target = site(w)
    trace.append(execute(w, 'work_construction', target, duration=12))
    if trace[-1]['status'] != 'completed':raise ValueError('Assigned work failed: ' + str(trace[-1]))
    return target, trace
