"""Read-only, loopback-only operator view; never a learner input."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3

from . import composition as comp, developmental as dev, storage


def projection(path):
    with closing(storage._connect(path, readonly=True)) as db:
        db.execute('BEGIN')
        world, _, _, head = storage._head(db)
        agents = [r[0] for r in db.execute('SELECT agent FROM development_people ORDER BY agent')]
        people = {}
        for agent, o in zip(agents, world.observe_batch(agents)):
            state = comp._person(db, agent)
            records = []
            for ident, kind in db.execute(
                    "SELECT id,kind FROM development_records WHERE agent=? AND kind LIKE 'h5_%' ORDER BY rowid DESC LIMIT 64", (agent,)):
                p = dev._read(db, 'development_records', ident, 'id')
                if 'native_events' in p and dev._source_events(db, path, list(p['native_events'])) != p['native_events']:
                    raise ValueError('panel evidence source missing')
                records.append(dict(id=ident, kind=kind, payload=p))
            h = state['h5']
            glosses = []
            for channel, e in h['hypotheses'].items():
                glosses.append(dict(channel=channel, actual_signal=channel.split(':', 1)[1],
                    inferred_features=e['possible'], uncertainty='ambiguous' if len(e['possible']) != 1 else 'single surviving hypothesis; not a guaranteed translation',
                    count=e['n'], evidence=e['evidence']))
            people[agent] = dict(observation=o, production=h['production'], hypotheses=glosses,
                recent_records=records, pending_attention=h['attention'], pending_message=h.get('pending_message'),
                counters=dict(external_teaching=h['external_teaching'], learned_associations=len(h['hypotheses']),
                    authored_decisions=h['authored_decisions'], random_ties=h['random_ties'],
                    protective_fallbacks=h['protective_fallbacks']),
                vocabulary_hash=dev.digest(h['production']))
        return dict(operator_only=True, read_only=True, native_head=head,
                    simulated_s=world.snapshot()['simulated_time_s'], people=people,
                    caution='Authored factorization and teaching. Glosses are uncertain inferences. No invented syntax claim.')


def server(path, port=8775):
    path = Path(path).resolve()
    comp.audit(path)
    assets = Path(__file__).parent / 'web' / 'learning'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
                self.send_error(403)
                return
            try:
                if self.path == '/api/learning':
                    body = json.dumps(projection(path)).encode('utf8')
                    content_type = 'application/json; charset=utf-8'
                elif self.path in ('/', '/panel.js', '/panel.css'):
                    name = {'/': 'index.html', '/panel.js': 'panel.js', '/panel.css': 'panel.css'}[self.path]
                    body = (assets / name).read_bytes()
                    content_type = {'/': 'text/html', '/panel.js': 'text/javascript', '/panel.css': 'text/css'}[self.path] + '; charset=utf-8'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy', "default-src 'self'; object-src 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
                self.send_error(409, 'Evidence unavailable: ' + str(error))

        def log_message(self, *_):
            pass

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8775)
    args = parser.parse_args()
    with server(args.db, args.port) as app:
        print(f'Operator learning panel: http://127.0.0.1:{app.server_port}/', flush=True)
        try:
            app.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
