"""Private fluctlight-style knowledge, lifespan, and astronomical projections.

This is an additive sidecar for new experiments. It does not add an actor to an
existing native save, does not reveal privileged world state, and does not
change the UW10W checkpoint format. A profile can only learn from the owner's
sanitized observation or from a provenance-bearing lesson from another
profile.
"""

from copy import deepcopy
import hashlib
import math


VERSION = 'ALICE-FLUCTLIGHT-1'
RESOURCE_KINDS = frozenset({'food', 'water', 'tree', 'rock', 'wood', 'fiber', 'stone', 'forage'})
DEFAULT_YEAR_DAYS = 360.0
DEFAULT_MONTHS = 12
DEFAULT_DAY_SECONDS = 86400.0
DEFAULT_LUNAR_DAYS = 29.53059


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f'{name} must be finite')
    return float(value)


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def _seeded_lifespan(seed, inhabitant_id):
    digest = hashlib.sha256(f'{seed}:{inhabitant_id}:lifespan'.encode()).digest()
    fraction = int.from_bytes(digest[:8], 'big') / 2**64
    return 50.0 * 365.0 + fraction * 40.0 * 365.0


def projected_lifespan_days(profile):
    """Return a transparent health-adjusted lifespan projection.

    Ordinary inhabitants vary between 50 and 90 healthy years. Current health
    shortens that projection by at most half; this is a sidecar estimate, not a
    claim about the native body's mortality law.
    """
    base = float(profile['base_lifespan_days'])
    if profile['role'] == 'teacher':
        return min(7.0, base)
    return base * (.5 + .5 * _clamp(profile.get('health', 1.0)))


def new_profile(inhabitant_id, *, role='inhabitant', seed=0, health=1.0,
                base_lifespan_days=None, native_observer_id=None):
    if not isinstance(inhabitant_id, str) or not inhabitant_id:
        raise ValueError('inhabitant_id is required')
    if role not in ('inhabitant', 'teacher'):
        raise ValueError('role must be inhabitant or teacher')
    health = _clamp(_finite(health, 'health'))
    if base_lifespan_days is None:
        base_lifespan_days = 7.0 if role == 'teacher' else _seeded_lifespan(seed, inhabitant_id)
    base_lifespan_days = _finite(base_lifespan_days, 'base_lifespan_days')
    if base_lifespan_days <= 0:
        raise ValueError('base_lifespan_days must be positive')
    return {
        'version': VERSION,
        'inhabitant_id': inhabitant_id,
        'native_observer_id': native_observer_id,
        'role': role,
        'age_days': 0.0,
        'health': health,
        'base_lifespan_days': base_lifespan_days,
        'alive': True,
        'knowledge': {
            'observations': [],
            'known_locations': {},
            'lessons': {},
        },
        'teaching': {'lessons_given': 0, 'recipients': []},
    }


def validate(profile):
    if not isinstance(profile, dict) or profile.get('version') != VERSION:
        raise ValueError('unsupported fluctlight profile')
    if not isinstance(profile.get('inhabitant_id'), str) or not profile['inhabitant_id']:
        raise ValueError('invalid fluctlight identity')
    if profile.get('native_observer_id') is not None and not isinstance(profile['native_observer_id'], str):
        raise ValueError('invalid native observer identity')
    if profile.get('role') not in ('inhabitant', 'teacher'):
        raise ValueError('invalid fluctlight role')
    for key in ('age_days', 'health', 'base_lifespan_days'):
        _finite(profile[key], key)
    if profile['age_days'] < 0 or profile['base_lifespan_days'] <= 0 or not 0 <= profile['health'] <= 1:
        raise ValueError('invalid fluctlight body state')
    if type(profile.get('alive')) is not bool:
        raise ValueError('invalid fluctlight life state')
    knowledge = profile.get('knowledge')
    if not isinstance(knowledge, dict) or not isinstance(knowledge.get('observations'), list):
        raise ValueError('invalid fluctlight knowledge')
    if not isinstance(knowledge.get('known_locations'), dict) or not isinstance(knowledge.get('lessons'), dict):
        raise ValueError('invalid fluctlight knowledge indexes')
    return profile


def advance(profile, seconds, *, health=None):
    profile = deepcopy(profile)
    validate(profile)
    seconds = _finite(seconds, 'seconds')
    if seconds < 0:
        raise ValueError('seconds must be nonnegative')
    if health is not None:
        profile['health'] = _clamp(_finite(health, 'health'))
    profile['age_days'] += seconds / DEFAULT_DAY_SECONDS
    profile['alive'] = profile['age_days'] < projected_lifespan_days(profile)
    return profile


def _public_entity(entity):
    fields = ('entity_id', 'kind', 'stage', 'species', 'alive', 'present', 'position_m', 'radius_m', 'mass_ug')
    return {key: deepcopy(entity[key]) for key in fields if key in entity}


def observe(profile, observation):
    """Record one owner's perceptual frame; hidden world state is discarded."""
    profile = deepcopy(profile)
    validate(profile)
    owner = profile.get('native_observer_id') or profile['inhabitant_id']
    if not isinstance(observation, dict) or observation.get('agent_id') != owner:
        raise ValueError('observation owner mismatch')
    own = observation.get('own_state')
    if not isinstance(own, dict) or 'position_m' not in own:
        raise ValueError('malformed own observation')
    tick = int(observation.get('tick', 0))
    visible = []
    for entity in observation.get('visible_entities', []):
        if entity.get('kind') in RESOURCE_KINDS:
            public = _public_entity(entity)
            visible.append(public)
            profile['knowledge']['known_locations'][public['entity_id']] = {
                'kind': public['kind'], 'position_m': public.get('position_m'), 'tick': tick,
                'observer': owner,
            }
    frame = {
        'tick': tick,
        'observer': owner,
        'own_position_m': deepcopy(own['position_m']),
        'visible_entities': visible,
    }
    profile['knowledge']['observations'] = (profile['knowledge']['observations'] + [frame])[-64:]
    return profile


def teach(teacher, learner, *, lesson='survival_basics', evidence_ids=None):
    """Transfer only teacher-held, observation-backed survival knowledge."""
    teacher = deepcopy(teacher); learner = deepcopy(learner)
    validate(teacher); validate(learner)
    if teacher['role'] != 'teacher' or not teacher['alive']:
        raise ValueError('only a living teacher can teach')
    if not learner['alive']:
        raise ValueError('learner is not alive')
    if lesson != 'survival_basics':
        raise ValueError('unsupported lesson')
    known = teacher['knowledge']['known_locations']
    selected = sorted(known) if evidence_ids is None else list(evidence_ids)
    if not selected or not set(selected) <= set(known):
        raise ValueError('lesson requires teacher-held observation evidence')
    evidence = [{'entity_id': key, **deepcopy(known[key])} for key in selected]
    learner['knowledge']['lessons'][lesson] = {
        'teacher': teacher['inhabitant_id'], 'evidence': evidence,
        'origin': 'teacher_observation_only', 'verified': False,
    }
    teacher['teaching']['lessons_given'] += 1
    if learner['inhabitant_id'] not in teacher['teaching']['recipients']:
        teacher['teaching']['recipients'].append(learner['inhabitant_id'])
    return teacher, learner


def calendar(simulated_seconds, *, year_days=DEFAULT_YEAR_DAYS, months=DEFAULT_MONTHS,
             day_seconds=DEFAULT_DAY_SECONDS, lunar_days=DEFAULT_LUNAR_DAYS,
             latitude_deg=0.0, axial_tilt_deg=23.44):
    """Return deterministic year/month, sun, moon, ellipse, and eclipse windows."""
    seconds = _finite(simulated_seconds, 'simulated_seconds')
    year_days = _finite(year_days, 'year_days'); day_seconds = _finite(day_seconds, 'day_seconds')
    lunar_days = _finite(lunar_days, 'lunar_days'); latitude_deg = _finite(latitude_deg, 'latitude_deg')
    axial_tilt_deg = _finite(axial_tilt_deg, 'axial_tilt_deg')
    if seconds < 0 or year_days <= 0 or day_seconds <= 0 or lunar_days <= 0 or months < 1:
        raise ValueError('invalid calendar configuration')
    days = seconds / day_seconds
    day_of_year = days % year_days
    month_days = year_days / months
    month_index = int(day_of_year // month_days)
    month_elapsed = day_of_year - month_index * month_days
    orbit = 2 * math.pi * day_of_year / year_days
    eccentricity = .0167
    mean_anomaly = orbit
    eccentric_anomaly = mean_anomaly + eccentricity * math.sin(mean_anomaly)
    true_anomaly = 2 * math.atan2(math.sqrt(1 + eccentricity) * math.sin(eccentric_anomaly / 2),
                                  math.sqrt(1 - eccentricity) * math.cos(eccentric_anomaly / 2))
    solar_longitude = true_anomaly % (2 * math.pi)
    tilt = math.radians(axial_tilt_deg); latitude = math.radians(latitude_deg)
    declination = math.asin(math.sin(tilt) * math.sin(solar_longitude))
    local_phase = (seconds % day_seconds) / day_seconds
    hour_angle = 2 * math.pi * (local_phase - .5)
    elevation = math.asin(_clamp(math.sin(latitude) * math.sin(declination) +
                                 math.cos(latitude) * math.cos(declination) * math.cos(hour_angle), -1, 1))
    moon_age = days % lunar_days
    moon_angle = 2 * math.pi * moon_age / lunar_days
    illumination = (1 - math.cos(moon_angle)) / 2
    phase_names = ('new', 'waxing_crescent', 'first_quarter', 'waxing_gibbous',
                   'full', 'waning_gibbous', 'third_quarter', 'waning_crescent')
    phase_index = int(((moon_age / lunar_days) * 8 + .5) % 8)
    near_node = min(moon_age, abs(moon_age - lunar_days / 2), lunar_days - moon_age)
    return {
        'day_number': int(days) + 1,
        'year_number': int(days // year_days) + 1,
        'year_progress': day_of_year / year_days,
        'month_number': month_index + 1,
        'month_progress': month_elapsed / month_days,
        'day_of_month': int(month_elapsed) + 1,
        'days_per_month': month_days,
        'sun': {
            'declination_deg': math.degrees(declination),
            'solar_longitude_deg': math.degrees(solar_longitude),
            'elevation_deg': math.degrees(elevation),
            'daylight_factor': _clamp(math.sin(elevation) * .5 + .5),
        },
        'moon': {
            'age_days': moon_age, 'phase': phase_names[phase_index],
            'illumination': illumination, 'distance_factor': 1 + .0549 * math.cos(moon_angle),
        },
        'orbit': {'eccentricity': eccentricity, 'true_anomaly_deg': math.degrees(true_anomaly % (2 * math.pi))},
        'eclipse_window': {
            'near_node_days': near_node,
            'solar_possible': moon_age <= .5 or moon_age >= lunar_days - .5,
            'lunar_possible': abs(moon_age - lunar_days / 2) <= .5,
        },
    }
