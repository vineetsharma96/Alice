"""Bounded Phase 9 research learner. Never imported by autonomous runtime policies.

Native execution and learning have separate commits. A reservation is not permission
to replay a physical action; finish() only verifies an already committed receipt.
"""
from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3

from . import storage
from .lease import Lease
from .wire import dumps

ROOT = Path(__file__).resolve().parents[1]


def sha(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def registration():
    seal = json.loads((ROOT / 'artifacts/phase9_registration.json').read_text(encoding='utf-8-sig'))
    for path, key in (('config/phase9_study.json', 'study_sha256'),
                      ('docs/PHASE9_PREREGISTRATION.md', 'preregistration_sha256')):
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != seal[key]:
            raise ValueError('preregistration seal mismatch')
    return json.loads((ROOT / 'config/phase9_study.json').read_text()), seal


def features(observation, kind, requested):
    if kind not in ('eat', 'drink') or type(requested) not in (float, int) or not math.isfinite(requested) or not 0 < requested <= 1:
        raise ValueError('unsupported research task')
    own = observation['own_state']
    if observation['agent_id'] != 'agent-1' or not own['alive'] or own['busy']:
        raise ValueError('requires own living idle actor')
    amount = int(own['inventory_ug'].get('food' if kind == 'eat' else 'water', '0')) / 1e9
    if not 0 <= amount <= 2:
        raise ValueError('inventory outside registered bounds')
    return [amount, float(requested), 1.0]


def predict(weights, x):
    return sum(a*b for a, b in zip(weights, x)) >= 0


def update(weights, x, label):
    if predict(weights, x) == label:
        return list(weights)
    scale = .25 * (1 if label else -1) / sum(v*v for v in x)
    return [max(-8, min(8, w + scale*v)) for w, v in zip(weights, x)]


def control(arm, state, x):
    records = [r for r in state['records'] if r['status'] == 'finished']
    if arm == 'online':
        return predict(state['weights'], x)
    if arm == 'frozen' or not records:
        return True
    if arm == 'nearest_memory':
        return min(records, key=lambda r: sum((a-b)**2 for a,b in zip(r['x'][:2], x[:2])))['label']
    if arm == 'bracket_memory':
        negative = [r['x'][0]-r['x'][1] for r in records if not r['label']]
        positive = [r['x'][0]-r['x'][1] for r in records if r['label']]
        if not negative: return True
        if not positive: return False
        return x[0]-x[1] >= (max(negative)+min(positive))/2
    raise ValueError('unknown arm')


def request(o, kind, mass, rid, targets=(), seconds=2):
    return dict(schema_version=1, run_id=o['run_id'], request_id=rid, agent_id='agent-1',
                observation_version=o['observation_version'], action_type=kind,
                target_ids=list(targets), parameters={} if kind == 'rest' else {'mass_kg':mass},
                requested_duration=seconds)


def execute(path, req):
    storage.advance(path, round(req['requested_duration']/.2), [(int(req['observation_version']), req)])
    o = storage.observe(path, ['agent-1'])[0]
    receipt = next(r for r in o['recent_action_results'] if r['request_id'] == req['request_id'])
    if receipt['status'] not in ('completed', 'rejected'):
        raise ValueError('no terminal native receipt')
    return receipt


def label_receipt(receipt):
    if receipt['status'] == 'completed': return True
    if receipt['status'] == 'rejected' and receipt['error_code'] == 'INSUFFICIENT_RESOURCE': return False
    raise ValueError('system failure is not a training label')


def world_head(path):
    with closing(storage._connect(path, readonly=True)) as db:
        world, config, metadata, head = storage._head(db)
        world.check_invariants()
        return world, config, metadata, head


class PolicyStore:
    """Small checksummed journal; verify the update chain on every read.

    Checksums detect accidental edits, not a malicious writer able to rewrite this
    entire database. Native journals and independently retained manifests are evidence.
    """
    def __init__(self, path):
        self.path = Path(path)

    @classmethod
    def create(cls, path, seed):
        spec, seal = registration()
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb'): pass
        state = dict(schema_version=1, study=spec['study'], registration=seal['study_sha256'],
                     owner='agent-1', seed=seed, weights=[0.,0.,0.], version=0, records=[])
        store = cls(path)
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE policy(singleton INTEGER PRIMARY KEY CHECK(singleton=1), payload TEXT, checksum TEXT)')
            db.execute('INSERT INTO policy VALUES(1,?,?)', (dumps(state), sha(state)))
            db.execute('PRAGMA user_version=1'); db.commit()
        return store

    def read(self):
        _, seal = registration()
        with closing(sqlite3.connect(f'{self.path.resolve().as_uri()}?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA user_version').fetchone()[0] != 1: raise ValueError('policy schema')
            payload, checksum = db.execute('SELECT payload,checksum FROM policy WHERE singleton=1').fetchone()
        state = json.loads(payload)
        if sha(state) != checksum or state['registration'] != seal['study_sha256'] or state['owner'] != 'agent-1':
            raise ValueError('policy integrity mismatch')
        weights = [0.,0.,0.]; version = 0; sources = set(); pending = False
        if len(state['records']) > 72: raise ValueError('training record bound')
        for r in state['records']:
            source = (r['request']['run_id'], r['request']['request_id'])
            if source in sources or pending or r['before_weights'] != weights: raise ValueError('policy chain mismatch')
            sources.add(source)
            if r['status'] == 'finished':
                if type(r['label']) is not bool or r['label'] != label_receipt(r['receipt']): raise ValueError('receipt label mismatch')
                weights = update(weights, r['x'], r['label']); version += 1
                if r['after_weights'] != weights: raise ValueError('update mismatch')
            elif r['status'] == 'reserved': pending = True
            else: raise ValueError('unknown trial state')
        if weights != state['weights'] or version != state['version']: raise ValueError('parameter/version mismatch')
        return state

    def _write(self, state):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('UPDATE policy SET payload=?,checksum=? WHERE singleton=1', (dumps(state), sha(state)))
            db.commit()

    def reserve(self, world_path, kind, mass, trial_id):
        with Lease(self.path), Lease(world_path):
            state = self.read()
            if len(state['records']) >= 72 or any(r['status'] == 'reserved' for r in state['records']):
                raise ValueError('record bound or unresolved reservation')
            world, config, _, head = world_head(world_path)
            if config['agency']['policy'] != 'none' or config['world']['population'] != 1 or config['world']['dt_s'] != .2:
                raise ValueError('requires registered native environment')
            o = world.observe_batch(['agent-1'])[0]; x = features(o, kind, mass)
            req = request(o, kind, mass, trial_id)
            if any(r['request']['run_id'] == req['run_id'] and r['request']['request_id'] == trial_id for r in state['records']):
                raise ValueError('duplicate training source')
            state['records'].append(dict(status='reserved', request=req, x=x, before_weights=state['weights'][:],
                before_head=head, before_checkpoint=world.checkpoint(), world_path=str(Path(world_path).resolve())))
            self._write(state)
            return req

    def finish(self, world_path, trial_id):
        with Lease(self.path), Lease(world_path):
            state = self.read()
            matches = [r for r in state['records'] if r['request']['request_id'] == trial_id]
            if len(matches) != 1: raise ValueError('unknown or ambiguous reservation')
            r = matches[0]
            if str(Path(world_path).resolve()) != r['world_path']: raise ValueError('foreign world path')
            # Even repeated finish calls reverify physical evidence; they never update twice.
            world, _, _, head = world_head(world_path)
            req = r['request']
            with closing(storage._connect(world_path, readonly=True)) as db:
                matches = [(json.loads(row[0]), row[1]) for row in db.execute('SELECT request,source FROM decisions')
                           if json.loads(row[0]).get('request_id') == trial_id]
            if matches != [(req, 'external')]: raise ValueError('missing or foreign committed request')
            expected = storage.load_native().World.restore(r['before_checkpoint'], req['run_id'])
            expected.submit(req, 'agent-1'); expected.step(10); expected.check_invariants()
            if expected.checkpoint() != world.checkpoint(): raise ValueError('physical source/head mismatch or incomplete action')
            receipt = next(v for v in world.observe_batch(['agent-1'])[0]['recent_action_results'] if v['request_id'] == trial_id)
            label = label_receipt(receipt)
            if r['status'] == 'finished':
                if r['receipt'] != receipt or r['after_head'] != head: raise ValueError('finished source changed')
                return r
            r.update(status='finished', receipt=receipt, label=label, after_head=head)
            state['weights'] = update(state['weights'], r['x'], label)
            r['after_weights'] = state['weights'][:]; state['version'] += 1
            self._write(state)
            return r

    def train(self, world_path, kind, mass, trial_id):
        with Lease(self.path), Lease(world_path):
            req = self.reserve(world_path, kind, mass, trial_id)
            execute(world_path, req)
            return self.finish(world_path, trial_id)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status'])
    parser.add_argument('--db', type=Path, required=True)
    args = parser.parse_args()
    s = PolicyStore(args.db).read()
    print(json.dumps({k:v for k,v in s.items() if k != 'records'} | {'records':len(s['records']),
        'pending':sum(r['status']=='reserved' for r in s['records'])}, indent=2))
