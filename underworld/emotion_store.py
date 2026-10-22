"""Opt-in emotion transactions on a COPY of a compatible weather world.

Weather physical journal remains replayable unchanged. Emotion journal includes
own episodes, native receipt links and cognitive before/after hashes. One atomic
transaction owns native/policy/cognition updates; no pending out-of-band learning.
"""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from . import emotion, weather_store as weather, weather_policy
from .lease import Lease

ROOT = Path(__file__).resolve().parents[1]


def sources():
    paths = ['underworld/emotion.py', 'underworld/emotion_store.py',
             'underworld/planning.py', 'underworld/policy.py']
    paths += list(json.loads((ROOT/'artifacts/weather_registration.json').read_text(encoding='utf8'))['files'])
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(set(paths))}


def token(w, policies, people):
    return weather.digest(weather.dumps(dict(native=w.checkpoint(), policies=policies, people=people)))


def attach(source, destination, agents=('agent-1',), mode='learned'):
    if not agents or len(set(agents)) != len(agents):raise ValueError('Select unique owners')
    # Backup API creates an exclusive destination. No original save mutations.
    weather.save(source, destination)
    with Lease(destination), closing(weather.connect(destination, False)) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='emotion_meta'").fetchone():
            raise ValueError('Already enrolled; resume this world instead')
        w, _, policies = weather.head(db)
        people = {a:emotion.initial(w.observe_batch([a])[0], mode) for a in agents}
        db.executescript('''CREATE TABLE emotion_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE emotion_head(id INTEGER PRIMARY KEY CHECK(id=1),people TEXT NOT NULL,hash TEXT NOT NULL);
            CREATE TABLE emotion_operations(seq INTEGER PRIMARY KEY,logical_id TEXT UNIQUE NOT NULL,
                command TEXT NOT NULL,before_hash TEXT NOT NULL,after_hash TEXT NOT NULL,result TEXT NOT NULL);''')
        db.execute('BEGIN IMMEDIATE')
        meta = dict(format='ALICE-EMOTION-1', sources=weather.dumps(sources()), initial=w.checkpoint(),
                    policies=weather.dumps(policies), people=weather.dumps(people),
                    weather_seq=str(db.execute('SELECT COALESCE(MAX(seq),0) FROM weather_operations').fetchone()[0]))
        db.executemany('INSERT INTO emotion_meta VALUES(?,?)', meta.items())
        db.execute('INSERT INTO emotion_head VALUES(1,?,?)', (weather.dumps(people), token(w, policies, people)))
        db.commit()
    return inspect(destination)


def head(db):
    w, meta, policies = weather.head(db)
    em = dict(db.execute('SELECT key,value FROM emotion_meta'))
    if em['format'] != 'ALICE-EMOTION-1' or json.loads(em['sources']) != sources():
        raise ValueError('Emotion sources/schema changed; use matching source, no silent migration')
    raw, checksum = db.execute('SELECT people,hash FROM emotion_head WHERE id=1').fetchone()
    people = json.loads(raw)
    if token(w, policies, people) != checksum:
        raise ValueError('Emotion head drift/corruption; all writes must use emotion coordinator')
    for a, s in people.items():
        emotion.validate(s)
        if a != s['owner'] or s['run_id'] != meta['run_id'] or s['tick'] != int(w.snapshot()['tick']):
            raise ValueError('Emotion owner/clock mismatch')
    return w, policies, people, em


def inspect(path):
    with closing(weather.connect(path)) as db:
        db.execute('BEGIN')
        w, policies, people, _ = head(db)
        return dict(snapshot=w.snapshot(), climate=w.weather_snapshot(), people=people,
                    policies=policies, hash=token(w, policies, people),
                    operations=db.execute('SELECT COUNT(*) FROM emotion_operations').fetchone()[0])


def apply(w, policies, people, command, logical_id, emit):
    before = {a:w.observe_batch([a])[0] for a in people}
    result = None; influence = None
    if command['kind'] == 'emotion-policy':
        agent = command['agent']
        if agent not in people:raise ValueError('Owner not enrolled')
        observation = before[agent]; p = policies.get(agent, weather_policy.state())
        base = weather_policy.choose(observation, deepcopy(p), command.get('mode', 'weather'))
        alternate, influence = emotion.influence(observation, people[agent], base)
        if alternate is None:
            result = emit(dict(kind='policy', agent=agent, mode=command.get('mode', 'weather')))
        else:
            # Existing routing constructs proposals only. Native decides acceptance
            # and completion; this is not learned motor control or construction.
            request = dict(schema_version=1, run_id=observation['run_id'], request_id='affect-'+logical_id,
                           agent_id=agent, observation_version=observation['tick'], action_type=alternate['action'],
                           target_ids=alternate['targets'], parameters=alternate['parameters'], requested_duration=alternate['duration'])
            receipt = emit(dict(kind='submit', request=request, principal=agent))
            accepted = receipt['status']=='accepted'
            if accepted:
                emit(dict(kind='step', ticks=math.ceil(alternate['duration']/observation['dt_s'])))
                receipt = next(r for r in w.observe_batch([agent])[0]['recent_action_results'] if r['request_id']==request['request_id'])
            s=people[agent]
            s['caution_failures']=0 if receipt['status']=='completed' else s['caution_failures']+1
            if s['caution_failures']>=3:
                s['caution_blocked_until']=int(w.snapshot()['tick'])+math.ceil(30/observation['dt_s'])
                s['caution_failures']=0
                influence['recovery']='three failed safety requests; 30 simulated seconds cooldown'
            result = dict(before=observation, choice=alternate, request=request, accepted=accepted, receipt=receipt,
                          after=w.observe_batch([agent])[0])
    elif command['kind'] in ('step', 'submit', 'force', 'policy', 'cohort'):
        result = emit(command)
    else:raise ValueError('Unsupported emotion command')
    updates = {}
    for agent, s in people.items():
        after = w.observe_batch([agent])[0]
        receipt = result.get('receipt') if isinstance(result, dict) else None
        if command['kind']=='submit' and command['request']['agent_id']==agent:receipt=result
        if receipt and receipt.get('agent_id') != agent:receipt=None
        # Terminal receipts may arrive during step. Only new own receipts qualify.
        old_receipts = {r['request_id']:r['status'] for r in before[agent]['recent_action_results']}
        terminal = [r for r in after['recent_action_results'] if r['status'] in ('completed','failed','rejected') and old_receipts.get(r['request_id']) != r['status']]
        if terminal:receipt=terminal[-1]
        own_result = isinstance(result, dict) and result.get('request', {}).get('agent_id') == agent
        goal = result.get('choice', {}).get('goal') if own_result else None
        updates[agent] = emotion.update(s, before[agent], after, f'{logical_id}:{agent}', receipt, goal)
    return dict(native=result, influence=influence, updates=updates)


def commit(path, command, logical_id, fault=None):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', logical_id):raise ValueError('Invalid operation identity')
    with Lease(path), closing(weather.connect(path, False)) as db:
        db.execute('BEGIN IMMEDIATE')
        w, policies, people, _ = head(db)
        prior = db.execute('SELECT command,result FROM emotion_operations WHERE logical_id=?',(logical_id,)).fetchone()
        if prior:
            if prior[0] != weather.dumps(command):raise ValueError('Conflicting logical operation')
            return json.loads(prior[1])
        if db.execute('SELECT COUNT(*) FROM emotion_operations').fetchone()[0]>=10000:
            raise ValueError('Emotion journal quota; archive evidence, never reset life')
        before = token(w, policies, people)
        def emit(c):
            if db.execute('SELECT COUNT(*) FROM weather_operations').fetchone()[0]>=25000:
                raise ValueError('Physical journal quota')
            old = weather.digest(w.checkpoint()); result = weather.apply(w, c, policies)
            db.execute('INSERT INTO weather_operations(command,before_hash,after_hash,result) VALUES(?,?,?,?)',
                       (weather.dumps(c), old, weather.digest(w.checkpoint()), weather.dumps(result)))
            return result
        result = apply(w, policies, people, command, logical_id, emit)
        w.check_invariants()
        if fault:fault('before_commit')
        after = token(w, policies, people)
        db.execute('UPDATE weather_head SET state=?,hash=?,policy=?,policy_hash=? WHERE id=1',
                   (w.checkpoint(),weather.digest(w.checkpoint()),weather.dumps(policies),weather.digest(weather.dumps(policies))))
        db.execute('UPDATE emotion_head SET people=?,hash=? WHERE id=1',(weather.dumps(people),after))
        db.execute('INSERT INTO emotion_operations(logical_id,command,before_hash,after_hash,result) VALUES(?,?,?,?,?)',
                   (logical_id,weather.dumps(command),before,after,weather.dumps(result)))
        db.commit()
        return json.loads(weather.dumps(result))


def replay(path):
    with closing(weather.connect(path)) as db:
        db.execute('BEGIN')
        final, final_policies, final_people, meta = head(db)
        from .weather_runtime import load
        w = load().World.restore(meta['initial'], final.snapshot()['run_id'])
        policies, people = json.loads(meta['policies']), json.loads(meta['people'])
        n = 0
        for ident, raw, old, new, expected in db.execute('SELECT logical_id,command,before_hash,after_hash,result FROM emotion_operations ORDER BY seq'):
            if token(w,policies,people)!=old:raise ValueError('Emotion replay before mismatch')
            actual = apply(w,policies,people,json.loads(raw),ident,lambda c:weather.apply(w,c,policies))
            if weather.dumps(actual)!=expected or token(w,policies,people)!=new:raise ValueError('Emotion replay update mismatch')
            n += 1
        if token(w,policies,people)!=token(final,final_policies,final_people):raise ValueError('Emotion replay final mismatch')
    physical = weather.replay(path)
    return dict(verified=True, operations=n, physical=physical, hash=token(w,policies,people))


class JournalWorld:
    """Assigned setup helpers may operate after attachment through this writer."""
    def __init__(self, path):self.path=path
    def _read(self, method, *args):
        with closing(weather.connect(self.path)) as db:
            w, _, _, _ = head(db)
            return getattr(w, method)(*args)
    def snapshot(self):return self._read('snapshot')
    def observe_batch(self, agents):return self._read('observe_batch', agents)
    def weather_snapshot(self):return self._read('weather_snapshot')
    def submit(self, request, principal):
        return commit(self.path, dict(kind='submit',request=request,principal=principal), 'submit-'+request['request_id'])['native']
    def step(self, ticks):
        ident = 'step-'+str(self.snapshot()['tick'])+'-'+str(ticks)
        return commit(self.path, dict(kind='step',ticks=ticks), ident)['native']
