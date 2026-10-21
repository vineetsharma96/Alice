import json
import threading
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from underworld import weather_store as store
from underworld.weather_runtime import climate, load
from underworld.weather_viewer import server


def forcing(w, duration=10, ident='forced-test'):
    return dict(id=ident, observation_version=w.snapshot()['tick'], duration_s=duration,
                temperature_c=-10, rain_mm_h=12, cloud_fraction=.9, wind_x_m_s=4, wind_y_m_s=1)


class WeatherViewerTests(unittest.TestCase):
    def test_forced_duration_applies_to_every_elapsed_interval(self):
        w=load().World(seed=53,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True,guided=True)
        w.configure_climate(climate());w.force_weather(forcing(w,duration=5),'operator');w.step(20)
        self.assertAlmostEqual(w.weather_snapshot()['exposure']['agent-1']['wetness'],.012*5,places=12)
        self.assertFalse(w.weather_snapshot()['forced'])

    def test_forcing_authority_staleness_idempotency_and_resume(self):
        closed=load().World(scripted=False,bodies=True);closed.configure_climate(climate())
        with self.assertRaises(ValueError):closed.force_weather(forcing(closed),'operator')
        w=load().World(seed=53,population=1,width=32,height=32,dt=.25,scripted=False,bodies=True,guided=True)
        w.configure_climate(climate());p=forcing(w)
        with self.assertRaises(ValueError):w.force_weather(p,'agent-1')
        w.force_weather(p,'operator');before=w.checkpoint()
        w.force_weather(p,'operator');self.assertEqual(before,w.checkpoint())
        with self.assertRaises(ValueError):w.force_weather(dict(p,rain_mm_h=1),'operator')
        w.step(13);resumed=load().World.restore(w.checkpoint(),'test')
        w.step(31);resumed.step(31)
        self.assertEqual(w.checkpoint(),resumed.checkpoint())
        self.assertFalse(w.weather_snapshot()['forced'])
        self.assertEqual(len(w.weather_snapshot()['forcing_history']),1)
        with self.assertRaises(ValueError):w.force_weather(dict(p,id='stale'),'operator')

    def test_readonly_observer_and_recorded_forcing_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'world.sqlite'
            store.initialize(path,population=1,guided=True)
            payload=dict(id='cli-force',observation_version='0',duration_s=10,temperature_c=-8,
                         rain_mm_h=10,cloud_fraction=.9,wind_x_m_s=2,wind_y_m_s=0)
            store.commit(path,dict(kind='force',parameters=payload))
            before=store.inspect(path)
            http=server(path,0);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{http.server_port}'
            try:
                for route in ('/','/weather.js','/scene.js','/vendor/three.module.min.js','/vendor/three.core.min.js','/api/weather'):
                    with urlopen(base+route) as response:
                        self.assertEqual(response.status,200)
                        self.assertIn('Content-Security-Policy',response.headers)
                        if route=='/api/weather':
                            packet=json.load(response)
                            self.assertTrue(packet['read_only']);self.assertTrue(packet['climate']['forced'])
                            self.assertNotIn('rng',packet['selected']['own_state']['weather'])
                with self.assertRaises(HTTPError) as caught:urlopen(Request(base+'/api/weather',data=b'{}',method='POST'))
                self.assertEqual(caught.exception.code,405)
                with self.assertRaises(HTTPError):urlopen(base+'/../HANDOFF.md')
                self.assertEqual(before,store.inspect(path))
            finally:http.shutdown();http.server_close();thread.join()
            store.commit(path,dict(kind='step',ticks=48))
            self.assertTrue(store.replay(path)['replay_matches'])


if __name__=='__main__':unittest.main()
