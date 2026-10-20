from contextlib import closing
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError

from underworld import storage,teaching
from underworld.config import load
from underworld.observer import make_server,Controller
from underworld.viewer import packet
from underworld.wire import dumps

ROOT=Path(__file__).resolve().parents[1]


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'run.sqlite'
        self.config=load(ROOT/'config/culture.toml');self.config['mode']='guided'
        storage.create(self.path,self.config)

    def tearDown(self):self.tmp.cleanup()

    def intervention(self,identifier='visible-book'):
        s=storage.inspect(self.path)
        return {'schema_version':1,'run_id':s['run_id'],'branch_id':s['branch_id'],'intervention_id':identifier,
            'observation_version':s['tick'],'kind':'place_book','parameters':{'entity_id':identifier,'x_m':3.4,'y_m':3,'mass_kg':.01,'energy_j':0,'text':'<script>Never execute source text</script>'}}

    def test_render_packets_are_consistent_and_byte_read_only(self):
        controller=Controller(self.path,readonly=True);before=self.path.read_bytes()
        for _ in range(5):
            p=packet(controller,'agent-1')
            self.assertEqual(p['protocol'],'underworld.viewer/1')
            self.assertEqual(p['snapshot']['tick'],p['selected']['tick'])
            self.assertEqual(p['snapshot']['state_hash'],storage.inspect(self.path)['state_hash'])
            self.assertEqual(p['coordinates']['physics_dimensions'],2)
            self.assertTrue(p['controls']['read_only'])
        self.assertEqual(self.path.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'read-only'):controller.control({'command':'step'})
        with self.assertRaisesRegex(ValueError,'read-only'):controller.intervene(self.intervention())

    def test_selected_memory_and_read_access_stay_source_bounded(self):
        teaching.intervene(self.path,self.intervention());controller=Controller(self.path)
        p=packet(controller,'agent-1')
        self.assertFalse(p['selected']['read_reports']);self.assertNotIn('Never execute',dumps(p['mind']))
        s=p['snapshot'];request={'schema_version':1,'run_id':s['run_id'],'request_id':'actual-read','agent_id':'agent-1','observation_version':s['tick'],
            'action_type':'read','target_ids':['visible-book'],'parameters':{},'requested_duration':1}
        storage._advance(self.path,5,[(0,request)])
        p=packet(controller,'agent-1');other=packet(controller,'agent-2')
        self.assertIn('Never execute',dumps(p['mind']));self.assertNotIn('Never execute',dumps(other['mind']))
        self.assertEqual(p['selected']['read_reports'][0]['origin_event_seq'],'1')
        self.assertEqual(p['mind']['agent'],'agent-1')

    def test_identical_recorded_actions_with_viewer_on_or_off_match(self):
        controller=Controller(self.path);copy_path=Path(self.tmp.name)/'off.sqlite';storage.save(self.path,'pair',copy_path)
        request=self.intervention()
        teaching.intervene(self.path,request);teaching.intervene(copy_path,request)
        for tick in range(12):
            # A real selected-agent perception, source/memory/event render packet between ticks.
            packet(controller,'agent-1',str(tick))
            storage._advance(self.path,1);storage._advance(copy_path,1)
        self.assertEqual(storage.inspect(self.path)['state_hash'],storage.inspect(copy_path)['state_hash'])
        self.assertEqual(storage.mind(self.path,'agent-1'),storage.mind(copy_path,'agent-1'))
        self.assertTrue(storage.replay(self.path)['replay_matches']);self.assertTrue(storage.replay(copy_path)['replay_matches'])

    def test_reconnect_cursor_catchup_gap_and_invalid_values(self):
        storage._advance(self.path,120);controller=Controller(self.path)
        first=packet(controller,'agent-1','0');second=packet(controller,'agent-1',first['event_window']['cursor'])
        self.assertEqual(first['snapshot']['state_hash'],second['snapshot']['state_hash'])
        self.assertTrue(first['event_window']['more'])
        self.assertGreater(int(second['events'][0]['seq']),int(first['events'][-1]['seq']))
        reset=packet(controller,'agent-1','99999');self.assertTrue(reset['event_window']['gap'])
        with closing(storage._connect(self.path)) as db:db.execute('DELETE FROM events WHERE seq<50')
        self.assertTrue(packet(controller,'agent-1','0')['event_window']['gap'])
        for value in ('-1','1.0','18446744073709551615'):
            with self.assertRaises(ValueError):packet(controller,'agent-1',value)
        with self.assertRaises(ValueError):packet(controller,'not-an-agent')

    def test_http_assets_tokens_and_operator_channel(self):
        server,c=make_server(self.path,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            before=self.path.read_bytes()
            for route in ('/viewer','/viewer.js','/scene.js','/viewer.css','/vendor/three.module.min.js','/vendor/three.core.min.js','/vendor/OrbitControls.js','/api/viewer?agent=agent-2'):
                with urlopen(base+route) as response:
                    self.assertEqual(response.status,200);self.assertIn("connect-src 'self'",response.headers['Content-Security-Policy'])
            self.assertEqual(before,self.path.read_bytes())
            req=self.intervention();headers={'Content-Type':'application/json','X-Observer-Token':c.token}
            with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/interventions',dumps(req).encode(),headers))
            self.assertEqual(error.exception.code,403)
            headers['X-Operator-Token']=c.operator_token
            with urlopen(Request(base+'/api/interventions',dumps(req).encode(),headers)) as response:self.assertEqual(json.load(response)['status'],'applied')
            with urlopen(base+'/api/viewer') as response:self.assertEqual(json.load(response)['operator_history'][0]['request'],req)
            self.assertTrue(storage.replay(self.path)['replay_matches'])
        finally:server.shutdown();c.close();server.server_close();thread.join(timeout=3)

    def test_read_only_attachment_does_not_take_existing_writer_lease(self):
        from underworld.lease import Lease
        errors=[]
        with Lease(self.path):
            def attach():
                try:packet(Controller(self.path,readonly=True),'agent-1')
                except Exception as error:errors.append(str(error))
            thread=threading.Thread(target=attach);thread.start();thread.join(timeout=3)
        self.assertFalse(thread.is_alive());self.assertFalse(errors)

    def test_packet_stays_on_one_commit_during_external_advancement(self):
        c=Controller(self.path,readonly=True);failures=[]
        def advance():
            try:storage._advance(self.path,60)
            except Exception as error:failures.append(str(error))
        thread=threading.Thread(target=advance);thread.start();seen=[]
        for _ in range(12):
            p=packet(c,'agent-1');seen.append(int(p['snapshot']['tick']))
            self.assertEqual(p['snapshot']['tick'],p['selected']['tick'])
            self.assertLessEqual(int(p['event_window']['cursor']),int(p['snapshot']['last_event_seq']))
        thread.join(timeout=15);self.assertFalse(thread.is_alive());self.assertFalse(failures)
        self.assertEqual(seen,sorted(seen));self.assertTrue(storage.replay(self.path)['replay_matches'])

    def test_pinned_assets_match_manifest_and_retain_license(self):
        root=ROOT/'underworld/web/vendor';manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(manifest['version'],'0.180.0')
        for name,record in manifest['files'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),record['sha256'])
        self.assertIn('MIT License',(root/'LICENSE.three').read_text(encoding='utf-8'))
        self.assertIn("from './three.module.min.js'",(root/'OrbitControls.js').read_text(encoding='utf-8'))
