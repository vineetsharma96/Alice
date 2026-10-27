import http.client as http_client
import json
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase
from underworld import life_store as store
from underworld.life_control import Control, server as control_server
from underworld.life_viewer import dashboard_packet


class ManualControlTests(TestCase):
    def test_paused_start_single_tick_and_resume(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)/'source.sqlite';path=Path(raw)/'life.sqlite'
            store.initialize_source(source,population=2);store.attach(source,path)
            c=Control(path)
            try:
                c.start();time.sleep(.1);self.assertEqual(int(c.status()['tick']),0)
                c.command({'command':'tick'})
                deadline=time.monotonic()+10
                while int(c.status()['tick'])<1 and time.monotonic()<deadline:time.sleep(.05)
                self.assertEqual(int(c.status()['tick']),1);self.assertTrue(c.status()['paused'])
                c.command({'command':'resume'});deadline=time.monotonic()+10
                while int(c.status()['tick'])<=1 and time.monotonic()<deadline:time.sleep(.05)
                c.command({'command':'pause'});self.assertGreater(int(c.status()['tick']),1)
                self.assertIsNone(c.status()['overall_tick_limit'])
                with self.assertRaises(ValueError):c.command({'command':'unknown'})
            finally:c.close()
            self.assertTrue(store.replay(path)['verified'])

    def test_bounded_batch_finishes_paused_and_run_until_is_exact(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)/'source.sqlite';path=Path(raw)/'life.sqlite'
            store.initialize_source(source,population=2);store.attach(source,path)
            c=Control(path)
            try:
                c.start();c.command({'command':'step_batch','ticks':3})
                deadline=time.monotonic()+10
                while c.status()['processing'] and time.monotonic()<deadline:time.sleep(.05)
                self.assertFalse(c.status()['processing']);self.assertTrue(c.status()['paused'])
                self.assertEqual(int(c.status()['tick']),3)
                self.assertEqual(c.status()['last_job']['state'],'completed')
                with self.assertRaisesRegex(ValueError,'align to the native timestep'):
                    c.command({'command':'run_until','simulated_s':float(c.status()['simulated_s'])+.1})
                target=float(c.status()['simulated_s'])+1.0
                c.command({'command':'run_until','simulated_s':target})
                deadline=time.monotonic()+10
                while c.status()['processing'] and time.monotonic()<deadline:time.sleep(.05)
                self.assertFalse(c.status()['processing']);self.assertTrue(c.status()['paused'])
                self.assertAlmostEqual(float(c.status()['simulated_s']),target)
            finally:c.close()

    def test_speed_pause_resume_and_cancel_batch_at_safe_boundaries(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)/'source.sqlite';path=Path(raw)/'life.sqlite'
            store.initialize_source(source,population=2);store.attach(source,path)
            c=Control(path)
            try:
                c.start()
                self.assertEqual(c.command({'command':'speed','value':5})['speed'],5.0)
                dilation=c.command({'command':'time_dilation','preset':'sao_300y_3w'})['time_dilation']
                self.assertEqual(dilation['preset'],'sao_300y_3w')
                self.assertGreater(dilation['scale'],5000)
                with self.assertRaisesRegex(ValueError,'unknown time-dilation preset'):
                    c.command({'command':'time_dilation','preset':'unbounded'})
                c.command({'command':'time_dilation','preset':'normal'})
                with self.assertRaises(ValueError):c.command({'command':'speed','value':2})
                c.command({'command':'speed','value':1})
                c.command({'command':'step_batch','ticks':1000})
                deadline=time.monotonic()+10
                while (not c.status()['processing'] or c.status()['job']['completed']<1) and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(c.status()['processing'])
                c.command({'command':'pause'})
                deadline=time.monotonic()+3
                while (not c.status()['job'] or c.status()['job']['state']!='paused') and time.monotonic()<deadline:time.sleep(.02)
                paused_tick=int(c.status()['tick']);self.assertEqual(c.status()['job']['state'],'paused')
                time.sleep(.2);self.assertEqual(int(c.status()['tick']),paused_tick)
                c.command({'command':'resume'})
                deadline=time.monotonic()+3
                while int(c.status()['tick'])<=paused_tick and time.monotonic()<deadline:time.sleep(.02)
                self.assertGreater(int(c.status()['tick']),paused_tick)
                c.command({'command':'cancel_step'})
                deadline=time.monotonic()+3
                while c.status()['processing'] and time.monotonic()<deadline:time.sleep(.02)
                self.assertFalse(c.status()['processing']);self.assertTrue(c.status()['paused'])
                self.assertEqual(c.status()['last_job']['state'],'cancelled')
            finally:c.close()

    def test_http_dashboard_and_control_authentication(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)/'source.sqlite';path=Path(raw)/'life.sqlite'
            store.initialize_source(source,seed=61,population=2);store.attach(source,path)
            http,control=control_server(path,0);control.start()
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            port=http.server_port

            def request(method,route,body=None,headers=None):
                connection=http_client.HTTPConnection('127.0.0.1',port,timeout=10)
                try:
                    headers={'Host':f'127.0.0.1:{port}',**(headers or {})}
                    if body is not None:
                        headers['Content-Type']='application/json'
                        body=json.dumps(body)
                    connection.request(method,route,body=body,headers=headers)
                    response=connection.getresponse()
                    return response.status,json.loads(response.read().decode() or '{}')
                finally:connection.close()

            try:
                status,control_state=request('GET','/api/life-control')
                self.assertEqual(status,200);token=control_state['token']
                status,dashboard=request('GET','/api/dashboard?agent=agent-1')
                self.assertEqual(status,200);self.assertEqual(dashboard['protocol'],'alice.dashboard/1')
                status,_=request('POST','/api/life-control',{'command':'speed','value':5})
                self.assertEqual(status,403)
                status,updated=request('POST','/api/life-control',{'command':'speed','value':5},{'X-Life-Control':token})
                self.assertEqual(status,200);self.assertEqual(updated['speed'],5.0)
            finally:
                control.close();http.shutdown();http.server_close();thread.join(timeout=5)

    def test_dashboard_packet_exposes_clock_population_and_bounded_mood_history(self):
        with tempfile.TemporaryDirectory() as raw:
            source=Path(raw)/'source.sqlite';path=Path(raw)/'life.sqlite'
            store.initialize_source(source,seed=61,population=2);store.attach(source,path)
            packet=dashboard_packet(path,'agent-2')
            self.assertEqual(packet['protocol'],'alice.dashboard/1')
            self.assertEqual(packet['selected']['agent_id'],'agent-2')
            self.assertEqual(packet['calendar']['day_number'],1)
            self.assertEqual(packet['population']['living_inhabitants'],2)
            self.assertIsNone(packet['population']['microbial_populations'])
            self.assertEqual(packet['payload_mode'],'projection')
            self.assertNotIn('raw',packet)
            self.assertTrue(all('evidence' not in sample for history in packet['mood_history'].values() for sample in history))
            self.assertIn('agent-1',packet['mood_history'])
            self.assertLessEqual(len(packet['events']),240)
            advanced=dashboard_packet(path,'agent-1',advanced=True)
            self.assertEqual(advanced['payload_mode'],'advanced')
            self.assertIn('raw',advanced)
            self.assertIn('entities',advanced['raw']['snapshot'])
