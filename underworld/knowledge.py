"""External knowledge is inert, private evidence, never native skill or executable code."""
import re
from contextlib import closing

from . import memory, storage
from .wire import loads

VERSION = 'knowledge/1'
PROFILES = {
    'none': None,
    'basic_survival': 'Food must be carried before eating. Approach accessible food, gather, then eat. Water and rest also matter.',
    'woodcraft': 'Gather finite wood, fiber and stone before crafting an axe. Planks require wood and a usable axe. Native laws decide outcomes.',
    'livestock_care': 'Observe an animal locally before choosing care. Carry food or water and transfer actual supplies. A claim is not a care result.',
    'specialist': None,
}
KINDS = ('external_initialization', 'operator_injection')


def text_payload(text):
    if type(text) is not str or not text.strip() or len(text.encode('utf-8')) > 1024:
        raise ValueError('knowledge text must contain 1..1024 UTF-8 bytes')
    return text


def prepare(profile, population, recipient=None, text=None):
    if profile not in PROFILES:raise ValueError('unknown knowledge profile')
    if profile == 'none':
        if recipient is not None or text is not None:raise ValueError('none profile has no recipient/text')
        return []
    if recipient not in [f'agent-{i+1}' for i in range(population)]:
        raise ValueError('choose one initial knowledge recipient')
    if profile == 'specialist':text = text_payload(text)
    elif text is not None:raise ValueError('custom text requires specialist profile')
    else:text = PROFILES[profile]
    return [(recipient, profile, text)]


def initialize(db, records, branch):
    # Called only inside creation's unpublished initial transaction.
    for agent, profile, text in records:
        memory.episode(db, agent, 'initial-knowledge', 0, 'external_initialization', {
            'text': text, 'source_type': 'external_initialization', 'source_id': 'initial-knowledge',
            'recipient': agent, 'branch_id': branch, 'delivery_tick': '0',
            'profile': profile, 'profile_version': VERSION, 'confidence': 'unverified',
            'skill_granted': False})
    memory.seal(db)


def inject(db, world, config, metadata, request):
    required = {'schema_version','run_id','branch_id','intervention_id','observation_version','kind','parameters'}
    if set(request) != required or type(request['schema_version']) is not int or request['schema_version'] != 1:
        raise ValueError('invalid injection envelope')
    snap = world.snapshot()
    if request['run_id'] != snap['run_id'] or request['observation_version'] != snap['tick']:
        raise ValueError('STALE_OBSERVATION: injection requires current run/tick')
    ident = request['intervention_id']
    if type(ident) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident):raise ValueError('invalid intervention id')
    params = request['parameters']
    if type(params) is not dict or set(params) != {'recipient','text'}:raise ValueError('injection accepts recipient and text only')
    agent = params['recipient'];text = text_payload(params['text'])
    if type(agent) is not str:raise ValueError('invalid recipient')
    memory.private_view(db, agent)
    own = world.observe_batch([agent])[0]['own_state']
    if not own['alive'] or not own.get('present',True):raise ValueError('recipient unavailable')
    from .config import episodic_enabled
    if not episodic_enabled(config):raise ValueError('explicit injection requires episodic retention')
    if db.execute("SELECT COUNT(*) FROM decisions WHERE source IN ('operator','operator_knowledge')").fetchone()[0] >= 256:
        raise ValueError('intervention quota reached')
    record = {'text': text, 'recipient': agent, 'source_type': 'operator_injection',
              'source_id': 'operator:' + ident, 'branch_id': metadata['branch_id'],
              'delivery_tick': snap['tick'], 'confidence': 'unverified', 'skill_granted': False}
    memory.episode(db, agent, 'injection:' + ident, int(snap['tick']), 'operator_injection', record)
    memory.seal(db)
    return {'status': 'recorded', 'source_type': 'operator_injection', 'recipient': agent,
            'tick': snap['tick'], 'branch_id': metadata['branch_id'], 'source_id': record['source_id'],
            'native_action': False, 'skill_granted': False}


def replay_result(db, request, tick):
    # Native replay does not re-teach or rebuild memory. Verify the retained external
    # record and replay a no-physics operation, then compare the journaled result.
    agent = request['parameters']['recipient']
    row = db.execute("SELECT payload FROM episodes WHERE agent=? AND source=? AND kind='operator_injection' AND tick=?",
                     (agent, 'injection:' + request['intervention_id'], tick)).fetchone()
    if not row:raise ValueError('injection replay evidence unavailable')
    record = loads(row[0])
    if record['text'] != request['parameters']['text'] or record['branch_id'] != request['branch_id']:
        raise ValueError('injection replay evidence mismatch')
    return {'status': 'recorded', 'source_type': 'operator_injection', 'recipient': agent,
            'tick': str(tick), 'branch_id': record['branch_id'], 'source_id': record['source_id'],
            'native_action': False, 'skill_granted': False}


def projection(db, agent):
    memory.private_view(db, agent)
    rows = db.execute("SELECT id,tick,kind,payload FROM episodes WHERE agent=? AND kind IN ('external_initialization','operator_injection','knowledge_test') ORDER BY id DESC LIMIT 64", (agent,))
    records = [{'episode_id': r[0], 'tick': r[1], 'kind': r[2], **loads(r[3])} for r in rows]
    return {'agent': agent, 'records': records, 'counts': {
        kind: db.execute('SELECT COUNT(*) FROM episodes WHERE agent=? AND kind=?', (agent,kind)).fetchone()[0]
        for kind in (*KINDS, 'book_read', 'unverified_report', 'knowledge_test')},
        'meaning': 'External claims are unverified; native practice alone grants skill.'}


def view(path, agent):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN');storage._head(db)
        return projection(db, agent)


def test_procedure(path, agent, episode_id):
    """Explicit bounded authored lab action. Only this actor's accessed record is used.

    Never navigates, heats, searches, retries or reads privileged apparatus truth.
    Caller must arrange physical prerequisites through ordinary native actions.
    """
    from . import culture
    from .lab_policy import Driver
    from .lease import Lease
    if type(episode_id) is not int or episode_id < 1:raise ValueError('invalid episode id')
    with Lease(path):
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute('BEGIN');_,config,_,_=storage._head(db);memory.private_view(db, agent)
            from .config import episodic_enabled
            if not episodic_enabled(config):raise ValueError('knowledge testing requires episodic retention')
            row = db.execute('SELECT kind,payload FROM episodes WHERE id=? AND agent=?', (episode_id,agent)).fetchone()
            if not row or row[0] not in (*KINDS, 'book_read', 'unverified_report'):raise ValueError('own accessible lesson required')
            record = loads(row[1]);procedure = culture.parse_procedure(record.get('text',''))
            if procedure is None:raise ValueError('no bounded apparatus procedure in lesson')
        driver = Driver(path, agent)
        observation = driver.observation()
        request_id = f"lab-{agent}-process_batch-{int(observation['tick'])}"
        # Reserve provenance before execution. memory.capture links the native terminal
        # receipt in its own physical transaction, including crash/resume boundaries.
        with closing(storage._connect(path)) as db:
            db.execute('BEGIN IMMEDIATE');_,_,meta,_ = storage._head(db)
            intent = {'lesson_episode_id': episode_id, 'source_type': record.get('source_type', row[0]),
                      'lesson_source_id': record['source_id'], 'branch_id': meta['branch_id'],
                      'request_id': request_id, 'execution_origin': 'authored_bounded_lab_driver',
                      'skill_granted_by_text': False}
            source = 'knowledge-intent:' + request_id
            prior = db.execute('SELECT payload FROM episodes WHERE agent=? AND source=?',(agent,source)).fetchone()
            if prior and loads(prior[0]) != intent:raise ValueError('conflicting knowledge test reservation')
            memory.episode(db,agent,source,int(observation['tick']),'knowledge_test_intent',intent)
            memory.seal(db);db.commit()
        receipt = driver.process(procedure['dial'])
        with closing(storage._connect(path, readonly=True)) as db:
            db.execute('BEGIN');storage._head(db)
            saved = db.execute("SELECT payload FROM episodes WHERE agent=? AND source=?",(agent,'knowledge-test:'+receipt['request_id'])).fetchone()
            if not saved:raise ValueError('native terminal knowledge receipt unavailable')
            return loads(saved[0])
