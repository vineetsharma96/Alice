"""Read-only, transaction-consistent projection for the Phase 8 renderer."""
from contextlib import closing
from . import storage,memory
from .config import episodic_enabled
from .wire import loads,counter


def packet(controller,agent=None,after='0'):
    after=counter(after)
    if after>2**63-1:raise ValueError('cursor exceeds journal integer range')
    with controller.lock,closing(storage._connect(controller.path,readonly=True)) as db:
        db.execute('BEGIN')
        world,config,metadata,hashed=storage._head(db)
        snapshot=world.snapshot();ids=[e['entity_id'] for e in snapshot['entities'] if e['kind']=='actor']
        selected=agent or ids[0]
        if selected not in ids:raise ValueError('unknown selected agent')
        observation=world.observe_batch([selected])[0]
        for receipt in observation['recent_action_results']:
            row=db.execute("SELECT request FROM decisions WHERE json_extract(request,'$.request_id')=? AND json_extract(request,'$.agent_id')=? ORDER BY id LIMIT 1",(receipt['request_id'],selected)).fetchone()
            if row:receipt['action_type']=loads(row[0])['action_type']
        first=db.execute('SELECT MIN(seq) FROM events').fetchone()[0];last=int(snapshot['last_event_seq'])
        gap=after>last or (first is not None and after<first-1)
        events=[loads(r[0]) for r in db.execute('SELECT payload FROM events WHERE seq>? ORDER BY seq LIMIT 96',(0 if after>last else after,))]
        history=[{'tick':r[0],'request':loads(r[1]),'result':loads(r[2])} for r in db.execute("SELECT tick,request,result FROM decisions WHERE source='operator' ORDER BY id DESC LIMIT 64")]
        snapshot.update(state_hash=hashed,branch_id=metadata['branch_id'],laws_version=metadata['laws_version'],parent_branch_id=metadata.get('parent_branch_id'),retained_replay_start_tick=metadata.get('retained_replay_start_tick',0))
        return {'protocol':'underworld.viewer/1','stream_id':snapshot['run_id']+':'+metadata['branch_id'],
            'snapshot':snapshot,'selected':observation,'mind':memory.private_view(db,selected,'book read report food water',episodic_enabled(config)),
            'events':events,'event_window':{'first_available':str(first or 0),'latest':str(last),'cursor':events[-1]['seq'] if events else str(last),'gap':gap,'more':bool(events and int(events[-1]['seq'])<last)},
            'operator_history':history,'controls':{'paused':controller.paused,'speed':controller.speed,'error':controller.error,'read_only':controller.readonly},
            'performance':{'advance_wall_s':controller.advance_wall,'advanced_simulated_s':controller.advanced_simulated,'simulation_work_s_per_wall_s':controller.advanced_simulated/controller.advance_wall if controller.advance_wall else None},
            'coordinates':{'mapping':'(x,y) metres -> (x,visual_height,-y)','physics_dimensions':2,'visual_height_authoritative':False}}
