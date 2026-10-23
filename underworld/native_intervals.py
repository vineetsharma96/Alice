"""Recover exact own action intervals from the existing native decision journal.

Read-only audit/telemetry helper for the UW9 profile, not a new policy or world.
"""
from . import storage
from .native import load_native


def action_intervals(db, owner, request_ids=None):
    head, _, metadata, _ = storage._head(db)
    initial=db.execute("SELECT state,tick FROM checkpoints WHERE name='initial'").fetchone()
    world=load_native().World.restore(initial[0],head.snapshot()['run_id'])
    end=int(head.snapshot()['tick']);pending={};found={}
    rows=iter(db.execute('SELECT tick,request,source,result FROM decisions WHERE id>? ORDER BY tick,id',
                         (metadata.get('replay_after_id',0),)))
    row=next(rows,None)
    def terminal():
        after=world.observe_batch([owner])[0]
        for receipt in after['recent_action_results']:
            rid=receipt['request_id']
            if rid not in pending or receipt['status'] not in ('completed','failed','rejected','expired'):continue
            before,request=pending.pop(rid)
            outcome={k:receipt[k] for k in ('request_id','status','error_code') if k in receipt}
            outcome.update(action_type=request['action_type'],result={},
                           estimated_cost_s=(int(after['tick'])-int(before['tick']))*before['dt_s'])
            found[rid]=dict(before=before,after=after,outcome=outcome)
    for tick in range(initial[1],end+1):
        while row is not None and row[0]==tick:
            request=storage.loads(row[1]);source=row[2]
            if source=='operator':world.intervene(request,'operator');world.step(0)
            elif source!='operator_knowledge':
                selected=(request.get('agent_id')==owner and request['request_id'] not in pending and request['request_id'] not in found
                          and (request_ids is None or request['request_id'] in request_ids))
                before=world.observe_batch([owner])[0] if selected else None
                receipt=world.submit(request,request['agent_id'])
                if storage.dumps(receipt)!=row[3]:raise ValueError('Native decision receipt differs from journal')
                if selected:pending[request['request_id']]=(before,request)
                terminal()
            row=next(rows,None)
        if tick<end:world.step(1);terminal()
    if row is not None:raise ValueError('Native interval journal contains future decisions')
    if world.checkpoint()!=head.checkpoint():raise ValueError('Native interval reconstruction differs from physical head')
    return found
