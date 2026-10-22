"""Additive observer panel on the unchanged weather 3D viewer. Read-only."""
import argparse
from contextlib import closing
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import emotion_store as store, weather_viewer


def packet(path, agent):
    with closing(store.weather.connect(path)) as db:
        db.execute('BEGIN')
        w, _, people, _ = store.head(db)
        if agent not in people:raise ValueError('Selected person has no attached emotional profile')
        recent=[]
        for seq, raw in db.execute('SELECT seq,result FROM emotion_operations ORDER BY seq DESC LIMIT 24'):
            r=json.loads(raw);u=r['updates'].get(agent)
            if u:recent.append(dict(seq=seq,event=u['event'],tick=u['observation_refs'][-1],stress=u['stress_after'],valence=u['after']['valence']))
        last=db.execute('SELECT result FROM emotion_operations ORDER BY seq DESC LIMIT 1').fetchone()
        return dict(protocol='alice.emotion-observer/1',read_only=True,privileged=True,
                    native_tick=w.snapshot()['tick'],native_hash=store.weather.digest(w.checkpoint()),
                    person=people[agent],timeline=list(reversed(recent)),
                    decision_influence=json.loads(last[0])['influence'] if last else None)


def server(path, port=8778):
    store.inspect(path)
    http=weather_viewer.server(path,port)
    base=http.RequestHandlerClass
    class Handler(base):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send(403,b'{"error":"Invalid host"}');return
            route=urlsplit(self.path)
            if route.path in ('/','/viewer'):
                original=(weather_viewer.WEB/'weather.html').read_text(encoding='utf8')
                panel='''<section id="emotion-panel" aria-label="Private emotional evidence">
                <h2>Personal experience &amp; affect</h2>
                <p>Observer diagnostics. Initial drives and appraisal rules are authored;
                cue expectations are learned privately. Slow stress is experimental;
                relationships, regulation and emotional language are not implemented.</p>
                <h3>Body, core affect &amp; profile</h3><pre id="affect-state"></pre>
                <h3>Recent stress / valence timeline</h3><pre id="affect-timeline"></pre>
                <h3>Episodes, appraisal &amp; factual memory links</h3><pre id="affect-appraisal"></pre>
                <h3>Learned expectations &amp; actual decision influence</h3><pre id="affect-learning"></pre>
                <p id="affect-source" role="status"></p></section>'''
                original=original.replace('</aside>',panel+'</aside>').replace('</head>','<script type="module" src="/emotion-panel.js"></script></head>')
                self.send(200,original.encode('utf8'),'text/html; charset=utf-8')
            elif route.path=='/emotion-panel.js':
                self.send(200,(Path(__file__).parent/'web/emotion-panel.js').read_bytes(),'text/javascript')
            elif route.path=='/api/emotion':
                try:
                    agent=parse_qs(route.query).get('agent',['agent-1'])[0]
                    self.send(200,json.dumps(packet(path,agent),allow_nan=False).encode())
                except (ValueError,RuntimeError,OSError) as error:
                    self.send(409,json.dumps(dict(error=str(error))).encode())
            else:super().do_GET()
    http.RequestHandlerClass=Handler
    return http


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8778)
    a=p.parse_args();server(a.db,a.port).serve_forever()


if __name__=='__main__':main()
