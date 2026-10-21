"""Read-only opt-in weather adapter for the existing 3D observer components."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import weather_store as store

WEB = Path(__file__).parent / 'web'
ASSETS = {'/':'weather.html','/viewer':'weather.html','/weather.js':'weather.js',
          '/weather.css':'weather.css','/scene.js':'scene.js',
          '/vendor/three.module.min.js':'vendor/three.module.min.js',
          '/vendor/three.core.min.js':'vendor/three.core.min.js',
          '/vendor/OrbitControls.js':'vendor/OrbitControls.js'}


def packet(path, agent):
    with closing(store.connect(path)) as db:
        db.execute('BEGIN')
        w, _, policies = store.head(db)
        selected=w.observe_batch([agent])[0]
        return dict(protocol='alice.weather/1',read_only=True,privileged_diagnostics=True,
                    snapshot=w.snapshot(),climate=w.weather_snapshot(),selected=selected,
                    selected_policy=policies.get(agent),state_hash=store.digest(w.checkpoint()))


def server(path, port=8777):
    path=Path(path).resolve()
    store.inspect(path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass

        def send(self,status,body,mime='application/json'):
            self.send_response(status)
            self.send_header('Content-Type',mime)
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(body)

        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send(403,b'{"error":"Invalid host"}');return
            parsed=urlsplit(self.path)
            if parsed.path=='/api/weather':
                try:
                    agent=parse_qs(parsed.query).get('agent',['agent-1'])[0]
                    result=packet(path,agent)
                    self.send(200,json.dumps(result,allow_nan=False).encode())
                except (ValueError,RuntimeError,OSError) as error:
                    self.send(409,json.dumps(dict(error=str(error))).encode())
            elif parsed.path in ASSETS:
                file=WEB/ASSETS[parsed.path]
                mime='text/html; charset=utf-8' if file.suffix=='.html' else 'text/css' if file.suffix=='.css' else 'text/javascript'
                self.send(200,file.read_bytes(),mime)
            else:self.send(404,b'{"error":"Not found"}')

        def do_POST(self):self.send(405,b'{"error":"Read-only observer; use the recorded CLI writer"}')

    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,required=True);parser.add_argument('--port',type=int,default=8777)
    args=parser.parse_args()
    server(args.db,args.port).serve_forever()


if __name__=='__main__':main()
