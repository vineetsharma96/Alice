"""Phase-0 contracts for the next integrated-life profile.

These records are shadow contracts only.  They are not written into existing
ALICE-LIFE-1 saves and they do not change native observation, action, mood, or
memory behaviour.  The next profile can use them as an immutable, replayable
boundary between native facts and private derived state.
"""

from copy import deepcopy
import hashlib
import math

from .wire import dumps


PROFILE = 'ALICE-LIFE-2'
CONTRACT_VERSION = 1
RECORD_TYPES = frozenset({'identity', 'observation', 'memory', 'body_need', 'affect_trace'})
PRIVACY_SCOPES = frozenset({'private', 'public_projection', 'operator_projection'})
PROVENANCE = frozenset({'native', 'derived', 'report', 'authored', 'operator', 'omitted'})
MEMORY_KINDS = frozenset({
    'episode', 'observation', 'report', 'belief', 'plan', 'procedure',
    'emotional_episode', 'self_model', 'relationship_event',
})
VALIDITY = frozenset({'active', 'superseded', 'invalidated'})
EXPLANATION_STATUS = frozenset({'recorded', 'derived', 'unavailable'})


def _text(value, name, maximum=128):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f'{name} must be a non-empty bounded string')
    return value


def _uint(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _number(value, name, low=None, high=None):
    if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f'{name} must be finite')
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f'{name} is outside its allowed range')
    return value


def _list_of_text(value, name, maximum=128):
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(item, str) for item in value):
        raise ValueError(f'{name} must be a bounded list of strings')
    return value


def _base(record_type, *, agent_id, run_id, branch_id='main', native_tick,
          observation_version, source_event_ids, provenance, privacy_scope):
    if record_type not in RECORD_TYPES:
        raise ValueError('unknown Phase-0 record type')
    _text(agent_id, 'agent_id'); _text(run_id, 'run_id'); _text(branch_id, 'branch_id')
    _uint(native_tick, 'native_tick'); _uint(observation_version, 'observation_version')
    _list_of_text(source_event_ids, 'source_event_ids')
    if provenance not in PROVENANCE:
        raise ValueError('unknown provenance')
    if privacy_scope not in PRIVACY_SCOPES:
        raise ValueError('unknown privacy scope')
    return {
        'profile': PROFILE,
        'contract_version': CONTRACT_VERSION,
        'record_type': record_type,
        'agent_id': agent_id,
        'run_id': run_id,
        'branch_id': branch_id,
        'native_tick': native_tick,
        'observation_version': observation_version,
        'source_event_ids': list(source_event_ids),
        'provenance': provenance,
        'privacy_scope': privacy_scope,
    }


def _without_checksum(record):
    value = deepcopy(record)
    value.pop('checksum', None)
    return value


def checksum(record):
    return hashlib.sha256(dumps(_without_checksum(record)).encode('utf8')).hexdigest()


def seal(record):
    value = validate(record)
    value['checksum'] = checksum(value)
    return value


def verify(record):
    value = validate(record)
    if value.get('checksum') != checksum(value):
        raise ValueError('Phase-0 record checksum mismatch')
    return value


def identity(*, agent_id, run_id, native_tick=0, observation_version=0,
             public_name, authored_traits, acquired_self_model=None,
             identity_revision=0, source_event_ids=None, branch_id='main'):
    value = _base('identity', agent_id=agent_id, run_id=run_id, branch_id=branch_id,
                  native_tick=native_tick, observation_version=observation_version,
                  source_event_ids=source_event_ids or [], provenance='derived', privacy_scope='private')
    _text(public_name, 'public_name', 128)
    if not isinstance(authored_traits, dict) or not isinstance(acquired_self_model or {}, dict):
        raise ValueError('identity traits and self model must be mappings')
    _uint(identity_revision, 'identity_revision')
    value.update(public_name=public_name, authored_traits=deepcopy(authored_traits),
                 acquired_self_model=deepcopy(acquired_self_model or {}),
                 identity_revision=identity_revision)
    return seal(value)


def observation(*, agent_id, run_id, native_tick, observation_version,
                own_state, visible_entities, audible_reports=None,
                read_reports=None, social_reports=None, recent_action_results=None,
                omissions=None, source_event_ids=None, branch_id='main'):
    value = _base('observation', agent_id=agent_id, run_id=run_id, branch_id=branch_id,
                  native_tick=native_tick, observation_version=observation_version,
                  source_event_ids=source_event_ids or [], provenance='native', privacy_scope='private')
    if not isinstance(own_state, dict) or not isinstance(visible_entities, list):
        raise ValueError('observation own_state and visible_entities are required')
    for name, item in (('audible_reports', audible_reports), ('read_reports', read_reports),
                       ('social_reports', social_reports), ('recent_action_results', recent_action_results)):
        if item is not None and not isinstance(item, list):
            raise ValueError(f'{name} must be a list')
    if omissions is not None and not isinstance(omissions, (list, dict)):
        raise ValueError('omissions must be a list or mapping')
    value.update(own_state=deepcopy(own_state), visible_entities=deepcopy(visible_entities),
                 audible_reports=deepcopy(audible_reports or []), read_reports=deepcopy(read_reports or []),
                 social_reports=deepcopy(social_reports or []),
                 recent_action_results=deepcopy(recent_action_results or []),
                 omissions=deepcopy(omissions or []))
    return seal(value)


def memory(*, agent_id, run_id, native_tick, observation_version,
           memory_id, memory_kind, content, source_refs, confidence=0.0,
           salience=0.0, validity='active', supersedes=None,
           provenance='derived', privacy_scope='private', branch_id='main'):
    value = _base('memory', agent_id=agent_id, run_id=run_id, branch_id=branch_id,
                  native_tick=native_tick, observation_version=observation_version,
                  source_event_ids=source_refs, provenance=provenance, privacy_scope=privacy_scope)
    _text(memory_id, 'memory_id');
    if memory_kind not in MEMORY_KINDS:
        raise ValueError('unknown memory kind')
    if not isinstance(content, dict):
        raise ValueError('memory content must be a mapping')
    if validity not in VALIDITY:
        raise ValueError('unknown memory validity')
    if supersedes is not None:
        _text(supersedes, 'supersedes')
    value.update(memory_id=memory_id, memory_kind=memory_kind, content=deepcopy(content),
                 confidence=_number(confidence, 'confidence', 0.0, 1.0),
                 salience=_number(salience, 'salience', 0.0, 1.0), validity=validity,
                 supersedes=supersedes)
    return seal(value)


def body_need(*, agent_id, run_id, native_tick, observation_version,
              hunger, thirst, fatigue, health, alive, source_event_ids=None,
              provenance='native', privacy_scope='private', branch_id='main'):
    value = _base('body_need', agent_id=agent_id, run_id=run_id, branch_id=branch_id,
                  native_tick=native_tick, observation_version=observation_version,
                  source_event_ids=source_event_ids or [], provenance=provenance, privacy_scope=privacy_scope)
    if type(alive) is not bool:
        raise ValueError('alive must be boolean')
    value.update(hunger=_number(hunger, 'hunger', 0.0, 1.0),
                 thirst=_number(thirst, 'thirst', 0.0, 1.0),
                 fatigue=_number(fatigue, 'fatigue', 0.0, 1.0),
                 health=_number(health, 'health', 0.0, 1.0), alive=alive)
    return seal(value)


def affect_trace(*, agent_id, run_id, tick_before, tick_after,
                 observation_version, body_signals, appraisal, fast_affect,
                 slow_mood, emotional_memory_refs=None, social_emotion_changes=None,
                 action_influence=None, explanation_status='recorded', source_event_ids=None,
                 provenance='derived', privacy_scope='private', branch_id='main'):
    if tick_after < tick_before:
        raise ValueError('tick_after must not precede tick_before')
    value = _base('affect_trace', agent_id=agent_id, run_id=run_id, branch_id=branch_id,
                  native_tick=tick_after, observation_version=observation_version,
                  source_event_ids=source_event_ids or [], provenance=provenance, privacy_scope=privacy_scope)
    if not all(isinstance(item, dict) for item in (body_signals, appraisal, fast_affect, slow_mood)):
        raise ValueError('affect trace state fields must be mappings')
    if explanation_status not in EXPLANATION_STATUS:
        raise ValueError('unknown explanation status')
    value.update(tick_before=tick_before, tick_after=tick_after,
                 body_signals=deepcopy(body_signals), appraisal=deepcopy(appraisal),
                 fast_affect=deepcopy(fast_affect), slow_mood=deepcopy(slow_mood),
                 emotional_memory_refs=list(emotional_memory_refs or []),
                 social_emotion_changes=deepcopy(social_emotion_changes or []),
                 action_influence=deepcopy(action_influence or {}),
                 explanation_status=explanation_status)
    return seal(value)


def validate(record):
    if not isinstance(record, dict):
        raise ValueError('Phase-0 record must be a mapping')
    required = {'profile', 'contract_version', 'record_type', 'agent_id', 'run_id',
                'branch_id', 'native_tick', 'observation_version', 'source_event_ids',
                'provenance', 'privacy_scope'}
    if not required <= set(record):
        raise ValueError('Phase-0 record is missing envelope fields')
    if record['profile'] != PROFILE or record['contract_version'] != CONTRACT_VERSION:
        raise ValueError('unsupported Phase-0 profile/version')
    record_type = record.get('record_type')
    allowed = {
        'identity': required | {'public_name', 'authored_traits', 'acquired_self_model', 'identity_revision', 'checksum'},
        'observation': required | {'own_state', 'visible_entities', 'audible_reports', 'read_reports',
                                   'social_reports', 'recent_action_results', 'omissions', 'checksum'},
        'memory': required | {'memory_id', 'memory_kind', 'content', 'confidence', 'salience',
                              'validity', 'supersedes', 'checksum'},
        'body_need': required | {'hunger', 'thirst', 'fatigue', 'health', 'alive', 'checksum'},
        'affect_trace': required | {'tick_before', 'tick_after', 'body_signals', 'appraisal',
                                    'fast_affect', 'slow_mood', 'emotional_memory_refs',
                                    'social_emotion_changes', 'action_influence',
                                    'explanation_status', 'checksum'},
    }.get(record_type) if isinstance(record_type, str) else None
    if allowed is None or not set(record) <= allowed:
        raise ValueError('Phase-0 record contains unknown fields')
    _base(record['record_type'], agent_id=record['agent_id'], run_id=record['run_id'],
          branch_id=record['branch_id'], native_tick=record['native_tick'],
          observation_version=record['observation_version'], source_event_ids=record['source_event_ids'],
          provenance=record['provenance'], privacy_scope=record['privacy_scope'])
    if record['record_type'] == 'identity':
        _text(record['public_name'], 'public_name')
        if not isinstance(record['authored_traits'], dict) or not isinstance(record['acquired_self_model'], dict):
            raise ValueError('invalid identity payload')
        _uint(record['identity_revision'], 'identity_revision')
    elif record['record_type'] == 'observation':
        if record['privacy_scope'] != 'private' or record['provenance'] != 'native':
            raise ValueError('observations must be private native records')
        if not isinstance(record['own_state'], dict) or not isinstance(record['visible_entities'], list):
            raise ValueError('invalid observation payload')
        for key in ('audible_reports', 'read_reports', 'social_reports', 'recent_action_results'):
            if not isinstance(record[key], list):
                raise ValueError('invalid observation report payload')
        if not isinstance(record['omissions'], (list, dict)):
            raise ValueError('invalid observation omissions payload')
    elif record['record_type'] == 'memory':
        _text(record['memory_id'], 'memory_id')
        if record['memory_kind'] not in MEMORY_KINDS or not isinstance(record['content'], dict):
            raise ValueError('invalid memory payload')
        _number(record['confidence'], 'confidence', 0.0, 1.0); _number(record['salience'], 'salience', 0.0, 1.0)
        if record['validity'] not in VALIDITY:
            raise ValueError('invalid memory validity')
    elif record['record_type'] == 'body_need':
        for key in ('hunger', 'thirst', 'fatigue', 'health'):_number(record[key], key, 0.0, 1.0)
        if type(record['alive']) is not bool:
            raise ValueError('invalid body_need alive field')
    elif record['record_type'] == 'affect_trace':
        _uint(record['tick_before'], 'tick_before'); _uint(record['tick_after'], 'tick_after')
        if record['tick_after'] < record['tick_before'] or record['explanation_status'] not in EXPLANATION_STATUS:
            raise ValueError('invalid affect trace envelope')
        for key in ('body_signals', 'appraisal', 'fast_affect', 'slow_mood'):
            if not isinstance(record[key], dict):
                raise ValueError('invalid affect trace state')
    return record
