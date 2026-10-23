"""Observer-only integrated diagnostics within the existing weather viewer."""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import life_store, weather_viewer
from .profile_derivation import derive

_shell=derive('underworld._life_viewer','underworld/mood_viewer.py',[
    ('from . import mood_store as store,weather_viewer','from . import life_store as store,weather_viewer'),
    ('mood_operations','life_operations'),
    ("protocol='alice.mood-observer/1'","protocol='alice.integrated-life/1'"),
])
packet=_shell.packet


def server(path,port=8781):
    http=_shell.server(path,port);base=http.RequestHandlerClass
    class Handler(base):
        def do_GET(self):
            route=urlsplit(self.path)
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send(403,b'{"error":"Invalid host"}');return
            if route.path=='/life-panel.js':
                self.send(200,(Path(__file__).parent/'web/life-panel.js').read_bytes(),'text/javascript');return
            if route.path in ('/','/viewer'):
                # Reuse the complete existing weather/mood viewer without
                # introducing a new world writer or exposing diagnostics to AI.
                html=(weather_viewer.WEB/'weather.html').read_text(encoding='utf8')
                panel='<section><h2>Integrated inhabitants</h2><p id="life-summary">Connecting</p><pre id="life-evidence"></pre><p>Human observer only. Authored rules and acquired evidence are shown separately. Viewing does not advance time.</p></section>'
                anchor='<h3>Selected inhabitant’s senses</h3>'
                html=html.replace(anchor,panel+anchor).replace('</head>','<script type="module" src="/life-panel.js"></script></head>')
                self.send(200,html.encode(),'text/html; charset=utf-8');return
            super().do_GET()
    http.RequestHandlerClass=Handler;return http


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8781)
    a=p.parse_args();server(a.db,a.port).serve_forever()


if __name__=='__main__':main()
