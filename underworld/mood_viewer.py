"""Read-only F4 overview within the existing native weather observer."""
import argparse
from contextlib import closing
import json
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

from . import mood_store as store,weather_viewer


def packet(path,agent):
    with closing(store.weather.connect(path)) as db:
        db.execute('BEGIN');w,_,people,meta=store.head(db)
        if agent not in people:raise ValueError('Inhabitant has no F4 profile')
        samples=[]
        for seq,raw in db.execute('SELECT seq,result FROM mood_operations ORDER BY seq DESC LIMIT 24'):
            u=json.loads(raw)['updates'].get(agent)
            if u:samples.append(dict(seq=seq,seconds=int(u['observation_refs'][-1].split(':')[-1])*w.snapshot()['dt_s'],stress=u['stress_after'],valence=u['mood_after']['valence']))
        return dict(protocol='alice.mood-observer/1',read_only=True,privileged=True,
                    native_tick=w.snapshot()['tick'],native_hash=store.weather.digest(w.checkpoint()),
                    person=people[agent],timeline=list(reversed(samples)),origin=json.loads(meta['origin']))


def server(path,port=8779):
    store.inspect(path);http=weather_viewer.server(path,port);base=http.RequestHandlerClass
    class Handler(base):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send(403,b'{"error":"Invalid host"}');return
            route=urlsplit(self.path)
            if route.path in ('/','/viewer'):
                html=(weather_viewer.WEB/'weather.html').read_text(encoding='utf8')
                panel='''<section id="mood-panel" aria-label="Slow mood and temperament">
                <h2>Slow mood &amp; temperament</h2><p id="mood-summary">Connecting</p>
                <label>Slow stress <progress id="mood-meter" max="1" value="0"></progress></label>
                <p id="mood-body"></p><p id="mood-traits"></p>
                <svg id="mood-curve" viewBox="0 0 300 72" width="100%" height="72" role="img" aria-label="Recent slow stress in simulation time"></svg>
                <p>Initial temperament is authored. Slow mood changes through actual bodily
                experience and recovery. No learned temperament or emotional language is claimed.</p>
                <details><summary>Private evidence and provenance</summary><pre id="mood-evidence"></pre></details>
                <p id="mood-source" role="status"></p></section>'''
                anchor='<h3>Selected inhabitant’s senses</h3>'
                if html.count(anchor)!=1:raise ValueError('Frozen viewer anchor changed')
                html=html.replace(anchor,panel+anchor).replace('</head>','<script type="module" src="/mood-panel.js"></script></head>')
                self.send(200,html.encode(),'text/html; charset=utf-8')
            elif route.path=='/mood-panel.js':self.send(200,(Path(__file__).parent/'web/mood-panel.js').read_bytes(),'text/javascript')
            elif route.path=='/api/mood':
                try:
                    agent=parse_qs(route.query).get('agent',['agent-1'])[0]
                    self.send(200,json.dumps(packet(path,agent),allow_nan=False).encode())
                except (ValueError,RuntimeError,OSError) as error:self.send(409,json.dumps(dict(error=str(error))).encode())
            else:super().do_GET()
    http.RequestHandlerClass=Handler;return http


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8779)
    a=p.parse_args();server(a.db,a.port).serve_forever()


if __name__=='__main__':main()
