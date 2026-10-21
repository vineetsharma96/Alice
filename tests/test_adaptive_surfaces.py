import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from underworld import adaptive as ad,adaptive_panel,storage

ROOT=Path(__file__).resolve().parents[1]


class AdaptiveSurfacesTests(unittest.TestCase):
    def test_cli_replays_same_scheduler_frame_without_extra_ticks(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'world.sqlite'
            def run(*args):return subprocess.run([sys.executable,str(ROOT/'scripts/adaptive_learner.py'),*args,'--db',str(path)],capture_output=True,text=True,timeout=30)
            self.assertEqual(run('init').returncode,0)
            first=run('step','--id','operator-cycle');self.assertEqual(first.returncode,0,first.stderr)
            head=storage.inspect(path)['state_hash']
            second=run('step','--id','operator-cycle');self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual(json.loads(first.stdout),json.loads(second.stdout))
            self.assertEqual(storage.inspect(path)['state_hash'],head)
            self.assertNotEqual(run('init').returncode,0)

    def test_panel_is_operator_only_read_only_and_loopback(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'world.sqlite';ad.initialize(path,53);before=ad.audit(path)
            with adaptive_panel.server(path,0) as app:
                worker=threading.Thread(target=app.serve_forever,daemon=True);worker.start()
                try:
                    base=f'http://127.0.0.1:{app.server_port}'
                    with urlopen(base+'/api/adaptive') as response:
                        packet=json.load(response);self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
                    self.assertTrue(packet['operator_only']);self.assertTrue(packet['read_only']);self.assertEqual(len(packet['people']),4)
                    for route in ('/','/adaptive.js','/panel.css'):
                        with urlopen(base+route) as response:self.assertEqual(response.status,200)
                    for request,code in [(Request(base+'/api/adaptive',method='POST',data=b'{}'),501),(Request(base+'/',headers={'Host':'untrusted.example'}),403),(Request(base+'/../.env'),404)]:
                        with self.assertRaises(HTTPError) as error:urlopen(request)
                        self.assertEqual(error.exception.code,code)
                finally:app.shutdown();worker.join(3)
            self.assertEqual(ad.audit(path),before)


if __name__=='__main__':unittest.main()
