"""Strict own-accessed feeding claim. Text is never native skill or truth."""
from .wire import loads,dumps


def parse(text):
    if type(text) is not str or not text.startswith('CARE '):return None
    try:claim=loads(text[5:],256)
    except ValueError:return None
    if type(claim) is not dict or set(claim)!={'task','material'} or claim['task']!='feed-v1':return None
    # Wood is an expressible false hypothesis, not a new native feed material.
    if claim['material'] not in ('food','plant_food','eggs','wood','water'):return None
    return claim


def text(material='food'):
    value='CARE '+dumps({'task':'feed-v1','material':material})
    if parse(value) is None:raise ValueError('unknown bounded care claim')
    return value


def lesson(db,agent,ident):
    if type(ident) is not int or ident<1:raise ValueError('invalid own care lesson id')
    row=db.execute("SELECT payload FROM episodes WHERE id=? AND agent=? AND kind IN ('external_initialization','operator_injection','book_read','unverified_report')",(ident,agent)).fetchone()
    if not row:raise ValueError('own accessed care lesson required')
    record=loads(row[0]);claim=parse(record.get('text',''))
    if claim is None:raise ValueError('lesson is not a bounded care procedure')
    return claim,record


def reserve(db,agent,task,request,tick):
    from . import memory
    ident=task.get('lesson_episode_id')
    if ident is None or request['action_type']!='offer_feed':return
    _,record=lesson(db,agent,ident)
    source='knowledge-intent:'+request['request_id']
    branch=loads(db.execute('SELECT metadata FROM run WHERE singleton=1').fetchone()[0])['branch_id']
    memory.episode(db,agent,source,tick,'knowledge_test_intent',{
        'lesson_episode_id':ident,'source_type':record.get('source_type','embodied_access'),
        'lesson_source_id':record['source_id'],'branch_id':branch,'lesson_branch_id':record.get('branch_id'),
        'request_id':request['request_id'],'execution_origin':'authored_assigned_care_executor',
        'skill_granted_by_text':False})
    memory.seal(db)
