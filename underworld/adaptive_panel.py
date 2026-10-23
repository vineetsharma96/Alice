"""Operator-only read-only evidence for the gap profile, never a policy input."""
import argparse
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3

from . import adaptive as ad,developmental as dev,storage


def projection(path):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');world,_,_,head=storage._head(db)
        people={}
        for agent, in db.execute('SELECT agent FROM development_people ORDER BY agent').fetchall():
            state=dev._person(db,agent,agent)
            if 'adaptive' not in state:continue
            state=ad._person(db,agent);h=state['adaptive'];o=world.observe_batch([agent])[0]
            labels={'kind:'+dev.digest(s['kind'])[:12]:s['kind']+' category' for s in h['sources'].values()}
            labels.update({'site:'+key:'visited landmark '+str(s['position']) for key,s in h['sites'].items()})
            glosses=[dict(signal=k,possible=[labels.get(f,f) for f in e['possible']],count=e['n'],
                evidence=e['evidence'],uncertainty='ambiguous' if len(e['possible'])!=1 else 'one surviving hypothesis; not guaranteed') for k,e in h['hypotheses'].items()]
            records=[]
            for ident,kind in db.execute("SELECT id,kind FROM development_records WHERE agent=? AND kind LIKE 'gap_%' ORDER BY rowid DESC LIMIT 64",(agent,)):
                records.append(dict(id=ident,kind=kind,payload=dev._read(db,'development_records',ident,'id')))
            people[agent]=dict(observation=o,plan=h['plan'],pending=h['pending'],glosses=glosses,
                quality=h['quality'],range_evidence=h['ranges'],sources=h['sources'],production=h['production'],records=records,
                counters=dict(external_teaching=h['external_teaching'],learned_associations=len(h['hypotheses'])+len(h['quality']),
                    authored_decisions=h['decisions'],completed_goals=h['goals'],situation_reports=h['reports_sent'],
                    authored_exploration=h['exploration'],protective_fallbacks=h['protective_fallbacks']))
        return dict(operator_only=True,read_only=True,native_head=head,simulated_s=world.snapshot()['simulated_time_s'],people=people)


def server(path,port=8776):
    ad.audit(path);web=Path(__file__).parent/'web'
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                self.send_error(403);return
            try:
                if self.path=='/api/adaptive':body=json.dumps(projection(path)).encode();kind='application/json'
                elif self.path in ('/','/adaptive.js','/panel.css'):
                    filename={'/':'adaptive.html','/adaptive.js':'adaptive.js','/panel.css':'learning/panel.css'}[self.path]
                    body=(web/filename).read_bytes();kind={'/':'text/html','/adaptive.js':'text/javascript','/panel.css':'text/css'}[self.path]
                else:self.send_error(404);return
                self.send_response(200);self.send_header('Content-Type',kind+'; charset=utf-8')
                self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; object-src 'none'; frame-ancestors 'none'")
                self.end_headers();self.wfile.write(body)
            except (ValueError,RuntimeError,OSError,sqlite3.Error):self.send_error(409,'Verified evidence unavailable')
        def log_message(self,*_):pass
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--port',type=int,default=8776)
    args=p.parse_args()
    with server(args.db,args.port) as app:
        print(f'Read-only adaptive evidence: http://127.0.0.1:{app.server_port}/',flush=True)
        try:app.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()
