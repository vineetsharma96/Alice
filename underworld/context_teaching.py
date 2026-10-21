"""Own-context teaching selection; the rule and attention affordance are authored."""
from contextlib import closing
import hashlib
from pathlib import Path

from . import adaptive as ad,developmental as dev,storage,wayfinding as wf
from .lease import Lease


def module_hash():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def attach(path,agents):
    with Lease(path),closing(storage._connect(path)) as db:
        db.execute('BEGIN IMMEDIATE')
        for agent in agents:
            state=ad._person(db,agent)
            if 'teaching_context' in state:raise ValueError('teaching profile already attached')
            state['teaching_context']=dict(disclosures={},pending=None,counter=0)
            dev._record(db,'teaching-contract-'+agent,agent,'gap_teaching_contract',dict(
                agent=agent,run_id=state['run_id'],module_sha256=module_hash(),
                prior='own novelty/disclosure model, real inventory, local peer, authored physical attention',budget=16))
            dev._put(db,'development_people',agent,state)
        db.commit()


def _person(db,agent):
    state=ad._person(db,agent)
    c=dev._read(db,'development_records','teaching-contract-'+agent,'id')
    if (c['module_sha256'],c['agent'],c['run_id'])!=(module_hash(),agent,state['run_id']):raise ValueError('teaching source/identity mismatch')
    if len(state['teaching_context']['disclosures'])>16:raise ValueError('disclosure budget reached')
    return state


def observe(path,agent):
    """No target/teacher supplied: attend over own scene and actual heard messages."""
    with Lease(path):
        with closing(storage._connect(path,readonly=True)) as db:
            state=_person(db,agent);a=state['adaptive']['attention']
        o=dev.own_observation(path,agent)
        if a:
            reports=[r for r in o['audible_reports'] if int(r['source_event_seq'])>a['after_seq']]
            if not reports:return dict(learned=False,attention=a['id'])
            message=max(reports,key=lambda r:int(r['source_event_seq']))
            learned=ad.learn_location(path,agent,message['speaker_id'],a['id'])
            return dict(learned=True,proof=learned)
        candidates=[e['entity_id'] for e in o['visible_entities'] if e['kind'] in ('food','water')]
        if not 1<=len(candidates)<=16:return dict(learned=False,reason='no bounded visible resource scene')
        ident='self-attention-'+str(state['version'])
        ad.begin_location(path,agent,ident,candidates)
        return dict(learned=False,attention=ident)


def teacher_step(path,agent,fault=None):
    """No recipient/target assignment and no query of another private state."""
    with Lease(path):
        ad.refresh(path,agent,True)
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');state=_person(db,agent);h=state['teaching_context']
            o=dev.own_observation(path,agent);pending=h['pending']
            if not pending:
                if max(o['own_state']['body']['hunger'],o['own_state']['body']['thirst'])>=.85:return dict(taught=False,reason='own urgent need; authored protection')
                peers=[e for e in o['visible_entities'] if e['kind']=='actor' and
                    sum((a-b)**2 for a,b in zip(e['position_m'],o['own_state']['position_m']))<=2.25]
                choices=[]
                for peer in peers:
                    for source in o['visible_entities']:
                        if source['kind'] not in ('food','water') or int(source['mass_ug'])<1000000:continue
                        if sum((a-b)**2 for a,b in zip(source['position_m'],o['own_state']['position_m']))>2.25:continue
                        if int(o['own_state']['inventory_ug'].get(source['kind'],0))<1000000:continue
                        key=dev.digest([peer['entity_id'],source['kind'],wf.cell(o['own_state']['position_m'])])
                        if key not in h['disclosures']:choices.append((key,peer['entity_id'],source['entity_id']))
                if not choices:return dict(taught=False,reason='no undisclosed own affordance with a local peer')
                if len(h['disclosures'])>=16:raise ValueError('teaching disclosure quota reached')
                key,peer,target=sorted(choices)[dev.random_index(state,len(choices))]
                h['counter']+=1
                pending=dict(id='context-'+str(h['counter']),key=key,peer=peer,target=target,text=None)
                h['pending']=pending;dev._put(db,'development_people',agent,state)
            db.commit()
        if pending['text'] is None:
            text=ad.encode_location(path,agent,pending['target'],True)
            with closing(storage._connect(path)) as db:
                db.execute('BEGIN IMMEDIATE');state=_person(db,agent)
                state['teaching_context']['pending']['text']=text
                dev._put(db,'development_people',agent,state);db.commit()
            pending['text']=text
        deposit=ad.perform(path,agent,pending['id']+'-deposit','deposit',[pending['target']],{'mass_kg':.001},fault=fault)
        if deposit['receipt']['status']!='completed':raise ValueError('context teaching deposit failed')
        speech=ad.perform(path,agent,pending['id']+'-speech','speak',parameters={'text':pending['text']},duration=2,fault=fault)
        if speech['receipt']['status']!='completed':raise ValueError('context teaching speech failed')
        if fault:fault('after_teaching_native')
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');state=_person(db,agent);h=state['teaching_context']
            h['disclosures'][pending['key']]=dict(peer=pending['peer'],target=pending['target'],understanding='unverified',utterance=pending['text'])
            h['pending']=None
            proof=ad._record(db,state,'context_teaching',dict(
                choice=pending,deposit_id=deposit['request']['request_id'],speech_id=speech['request']['request_id'],
                native_events=dict(deposit['native_events'],**speech['native_events']),
                origin='own-context selection using authored disclosure model; not learned intention'))
            db.commit()
        return dict(taught=True,proof=proof,deposit=deposit,speech=speech)


def audit(path):
    result=ad.audit(path)
    with closing(storage._connect(path,readonly=True)) as db:
        for agent,s in result['people'].items():
            if 'teaching_context' not in s:continue
            state=_person(db,agent)
            proofs=[dev._read(db,'development_records',r[0],'id') for r in db.execute("SELECT id FROM development_records WHERE agent=? AND kind='gap_context_teaching'",(agent,))]
            for key,entry in state['teaching_context']['disclosures'].items():
                matches=[p for p in proofs if p['choice']['key']==key]
                if len(matches)!=1 or entry!=dict(peer=matches[0]['choice']['peer'],target=matches[0]['choice']['target'],understanding='unverified',utterance=matches[0]['choice']['text']):
                    raise ValueError('teaching model lacks own disclosure evidence')
    return result
