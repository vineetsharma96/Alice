"""Read-only living-world telemetry and the Alice observer dashboard."""

import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import webbrowser

from . import life_store, weather_store as weather, weather_viewer
from .profile_derivation import derive


# Preserve the small historical mood endpoint used by existing tools.
_shell = derive('underworld._life_viewer', 'underworld/mood_viewer.py', [
    ('from . import mood_store as store,weather_viewer', 'from . import life_store as store,weather_viewer'),
    ('mood_operations', 'life_operations'),
    ("protocol='alice.mood-observer/1'", "protocol='alice.integrated-life/1'"),
])
packet = _shell.packet

WEB = Path(__file__).parent / 'web'
ASSETS = {
    '/': ('dashboard.html', 'text/html; charset=utf-8'),
    '/viewer': ('dashboard.html', 'text/html; charset=utf-8'),
    '/dashboard.html': ('dashboard.html', 'text/html; charset=utf-8'),
    '/dashboard.css': ('dashboard.css', 'text/css'),
    '/dashboard.js': ('dashboard.js', 'text/javascript'),
    '/scene.js': ('scene.js', 'text/javascript'),
    '/weather.js': ('weather.js', 'text/javascript'),
    '/weather.css': ('weather.css', 'text/css'),
    '/vendor/three.module.min.js': ('vendor/three.module.min.js', 'text/javascript'),
    '/vendor/three.core.min.js': ('vendor/three.core.min.js', 'text/javascript'),
    '/vendor/OrbitControls.js': ('vendor/OrbitControls.js', 'text/javascript'),
}


def _json(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _tick_from_refs(refs, fallback):
    if isinstance(refs, list) and refs:
        try:
            return int(str(refs[-1]).rsplit(':', 1)[-1])
        except (TypeError, ValueError):
            pass
    return int(fallback)


def _mood_explanation(update):
    appraisal = update.get('appraisal') or {}
    classification = appraisal.get('classification', 'observed_outcome')
    harm = float(appraisal.get('harm', 0.0) or 0.0)
    relief = float(appraisal.get('relief', 0.0) or 0.0)
    if harm > 0.01:
        return 'Recorded harm increased during this interval; the cause is not inferred.'
    if relief > 0.01:
        return 'Recorded bodily relief during this interval.'
    labels = {
        'scarcity': 'The action encountered a recorded resource shortage.',
        'approach_error': 'The action ended with a recorded approach error.',
        'contention': 'The action was affected by recorded contention.',
        'stale_observation': 'The action used a stale observation.',
        'unavailable_not_proven_depleted': 'The target was unavailable; depletion was not proven.',
        'observed_outcome': 'The trace records an observed native outcome.',
    }
    return labels.get(classification, f'Recorded outcome: {classification}.')


def _event_detail(event):
    if not isinstance(event, dict):
        return ''
    detail = event.get('detail') or event.get('description') or ''
    if detail:
        return str(detail)
    if event.get('type') == 'death':
        return 'Recorded death event.'
    if event.get('type') == 'tick':
        return 'Native world tick committed.'
    return ''


def _dashboard_entity(entity):
    fields = ('entity_id', 'kind', 'stage', 'species', 'alive', 'present', 'position_m',
              'radius_m', 'mass_ug', 'body')
    return {field: _json(entity[field]) for field in fields if field in entity}


def _dashboard_snapshot(snapshot):
    fields = ('protocol', 'run_id', 'branch_id', 'parent_branch_id', 'laws_version',
              'mode', 'seed', 'tick', 'simulated_time_s', 'dt_s', 'world_bounds_m',
              'event_counts', 'outstanding_actions')
    projected = {field: _json(snapshot[field]) for field in fields if field in snapshot}
    projected['entities'] = [_dashboard_entity(entity) for entity in snapshot.get('entities', [])]
    return projected


def _dashboard_person(person):
    life = person.get('life', {}) if isinstance(person, dict) else {}
    return {'life': {'last_decision': _json(life.get('last_decision'))} if isinstance(life, dict) else {}}


def dashboard_packet(path, agent=None, history_limit=240, advanced=False):
    """Return bounded, operator-facing telemetry from one consistent head."""
    with closing(weather.connect(path)) as db:
        db.execute('BEGIN')
        world, policies, people, meta = life_store.head(db)
        snapshot = world.snapshot()
        actors = [e for e in snapshot['entities'] if e.get('kind') == 'actor']
        ids = sorted(e['entity_id'] for e in actors)
        selected_id = agent or (ids[0] if ids else '')
        if selected_id not in ids:
            raise ValueError('unknown selected inhabitant')
        selected = world.observe_batch([selected_id])[0]
        climate = world.weather_snapshot()
        dt_s = float(snapshot.get('dt_s', 0.25))
        mood = {ident: [] for ident in ids}
        events = []
        life_rows = db.execute('SELECT logical_id,command,result FROM life_operations ORDER BY seq DESC LIMIT ?', (history_limit,)).fetchall()
        for logical_id, command_text, result_text in reversed(life_rows):
            command = json.loads(command_text)
            result = json.loads(result_text)
            updates = result.get('updates') if isinstance(result, dict) else None
            if isinstance(updates, dict):
                for ident, update in updates.items():
                    if ident not in mood:
                        continue
                    tick = _tick_from_refs(update.get('observation_refs'), snapshot['tick'])
                    appraisal = update.get('appraisal') or {}
                    sample = {
                        'tick': tick,
                        'seconds': tick * dt_s,
                        'stress': float(update.get('stress_after', 0.0)),
                        'valence': float((update.get('mood_after') or {}).get('valence', 0.0)),
                        'arousal': float((update.get('after') or {}).get('arousal', 0.0)),
                        'event': update.get('event'),
                        'classification': appraisal.get('classification', 'observed_outcome'),
                        'explanation': _mood_explanation(update),
                    }
                    if advanced:
                        sample['evidence'] = update.get('observation_refs', [])
                    mood[ident].append(sample)
                    event_entry = {
                        'tick': tick, 'seconds': tick * dt_s, 'type': 'mood_update',
                        'agent_id': ident, 'detail': _mood_explanation(update),
                    }
                    if advanced:
                        event_entry['evidence'] = update.get('observation_refs', [])
                    events.append(event_entry)
            native = result.get('native') if isinstance(result, dict) else None
            native_events = native if isinstance(native, list) else [native] if isinstance(native, dict) else []
            for event in native_events:
                if not isinstance(event, dict):
                    continue
                tick = int(event.get('tick', snapshot['tick']))
                event_type = event.get('type') or event.get('status') or command.get('kind', 'native')
                events.append({'tick': tick, 'seconds': tick * dt_s, 'type': event_type,
                               'agent_id': event.get('agent_id', ''), 'detail': _event_detail(event),
                               'request_id': event.get('request_id', '')})
            if command.get('kind') == 'emotion-policy':
                ident = command.get('agent')
                events.append({'tick': int(snapshot['tick']), 'seconds': float(snapshot['simulated_time_s']),
                               'type': 'decision', 'agent_id': ident, 'detail': 'Recorded policy decision interval.',
                               'request_id': logical_id})
        for ident in mood:
            mood[ident] = sorted(mood[ident], key=lambda item: item['tick'])[-history_limit:]
        events = sorted(events, key=lambda item: (item['tick'], item['type']))[-history_limit:]

        edges = []
        for owner, person in people.items():
            life = person.get('life', {}) if isinstance(person, dict) else {}
            relationships = life.get('relationships', {}) if isinstance(life, dict) else {}
            if isinstance(relationships, dict):
                for target, edge in relationships.items():
                    if isinstance(edge, dict):
                        edges.append({'from': owner, 'to': target, **_json(edge)})

        population = {
            'living_inhabitants': sum(1 for e in actors if e.get('alive', True) and e.get('present', True)),
            'inhabitants': len(actors),
            'animals': sum(1 for e in snapshot['entities'] if e.get('kind') == 'animal' and e.get('alive', True)),
            'plants': sum(1 for e in snapshot['entities'] if e.get('kind') in ('tree', 'forage')),
            'microbial_populations': None,
            'microbial_note': 'Microbial populations are not exposed by this native runtime.',
            'total_entities': len(snapshot['entities']),
            'event_counts': _json(snapshot.get('event_counts', {})),
        }
        day_s = float(climate.get('day_s', 86400) or 86400)
        simulated_s = float(snapshot.get('simulated_time_s', 0.0))
        day_index = int(simulated_s // day_s) + 1
        day_elapsed = simulated_s % day_s
        calendar = {
            'day_number': day_index,
            'time_of_day_s': day_elapsed,
            'time_of_day_label': f'{int(day_elapsed // 3600):02d}:{int((day_elapsed % 3600) // 60):02d}',
            'day_length_s': day_s,
            'year_index': climate.get('year_index'),
            'season': climate.get('season'),
        }
        packet = {
            'protocol': 'alice.dashboard/1',
            'read_only': True,
            'payload_mode': 'advanced' if advanced else 'projection',
            'snapshot': _dashboard_snapshot(snapshot),
            'climate': _json(climate),
            'calendar': calendar,
            'selected': _json(selected),
            'selected_person': _dashboard_person(people[selected_id]),
            'people': {ident: {'agent_id': ident} for ident in people},
            'mood_history': mood,
            'events': events,
            'relationships': edges,
            'population': population,
            'state_hash': weather.digest(world.checkpoint()),
            'operation_count': int(db.execute('SELECT COUNT(*) FROM life_operations').fetchone()[0]),
            'source': {'run_id': snapshot['run_id'], 'branch_id': snapshot['branch_id'],
                       'laws_version': snapshot['laws_version'], 'mode': snapshot['mode']},
            'unsupported': {
                'target_specific_anger': 'Unavailable: this runtime has no target-specific anger field.',
                'reproduction': 'Unavailable in the native integrated-life runtime.',
                'births_deaths': 'Shown only when present in native event counts; no lifecycle sidecar is attached here.',
                'reserved_inventory': 'Unavailable: native observation exposes carried quantities only.',
                'microbial_count': 'Unavailable: no native microbial individuals are exposed.',
            },
        }
        if advanced:
            packet['raw'] = {'snapshot': _json(snapshot), 'people': _json(people), 'policies': _json(policies)}
        return packet


def server(path, port=8781):
    path = Path(path).resolve()
    life_store.inspect(path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, mime='application/json'):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, allow_nan=False)
            if isinstance(body, str):
                body = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {'error': 'Invalid host'})
            route = urlsplit(self.path)
            try:
                if route.path == '/favicon.ico':
                    return self.send(204, b'', 'image/x-icon')
                if route.path == '/api/dashboard':
                    query = parse_qs(route.query)
                    agent = query.get('agent', [None])[0]
                    advanced = query.get('detail', [''])[0] == 'advanced'
                    return self.send(200, json.dumps(dashboard_packet(path, agent, advanced=advanced), allow_nan=False))
                if route.path == '/api/mood':
                    agent = parse_qs(route.query).get('agent', ['agent-1'])[0]
                    return self.send(200, json.dumps(packet(path, agent), allow_nan=False))
                if route.path == '/api/weather':
                    agent = parse_qs(route.query).get('agent', ['agent-1'])[0]
                    with closing(weather.connect(path)) as db:
                        db.execute('BEGIN')
                        world, _, policies = weather.head(db)
                        selected = world.observe_batch([agent])[0]
                        result = dict(protocol='alice.weather/1', read_only=True, privileged_diagnostics=True,
                                      snapshot=world.snapshot(), climate=world.weather_snapshot(), selected=selected,
                                      selected_policy=policies.get(agent), state_hash=weather.digest(world.checkpoint()))
                    return self.send(200, json.dumps(result, allow_nan=False))
                if route.path in ASSETS:
                    name, mime = ASSETS[route.path]
                    return self.send(200, (WEB / name).read_bytes(), mime)
                if route.path == '/life-panel.js':
                    return self.send(200, (WEB / 'life-panel.js').read_bytes(), 'text/javascript')
                return self.send(404, {'error': 'Not found'})
            except (ValueError, RuntimeError, OSError) as error:
                return self.send(409, {'error': str(error)})

        def do_POST(self):
            return self.send(405, {'error': 'Read-only telemetry; use the life-control writer endpoint.'})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8781)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    http = server(args.db, args.port)
    try:
        url = f'http://127.0.0.1:{http.server_port}/'
        print(json.dumps(dict(url=url, db=str(args.db.resolve()), read_only=True)), flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        http.server_close()


if __name__ == '__main__':
    main()
