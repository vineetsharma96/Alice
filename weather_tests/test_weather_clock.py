import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from underworld.weather_runtime import climate, load


class WeatherClockTests(unittest.TestCase):
    def world(self, dt=.1, enabled=True, bodies=False):
        w = load().World(seed=53, population=1, width=32, height=32, dt=dt,
                         scripted=False, bodies=bodies, run_id='weather-tests')
        w.configure_climate(climate(enabled=enabled))
        return w

    def test_invalid_config_and_new_world_only(self):
        for key, value in [('year_s', float('nan')), ('year_s', 0), ('transition_s', float('inf')),
                           ('change_s', -1), ('temperature_bias_c', 31), ('enabled', 1), ('year_s', True)]:
            w = load().World(scripted=False)
            with self.assertRaises((ValueError, RuntimeError)):
                w.configure_climate(dict(climate(), **{key: value}))
        w = self.world()
        with self.assertRaises(ValueError):
            w.configure_climate(climate())
        w = load().World(scripted=False)
        w.step(1)
        with self.assertRaises(ValueError):
            w.configure_climate(climate())

    def test_repeatability_fractional_resume_and_inspection(self):
        a, b = self.world(), self.world()
        a.step(975); b.step(975)
        self.assertEqual(a.checkpoint(), b.checkpoint())
        self.assertGreater(a.weather_snapshot()['transition_end_s'], a.snapshot()['simulated_time_s'])
        saved = a.checkpoint()
        for _ in range(3):
            a.snapshot(); a.weather_snapshot(); a.observe_batch(['agent-1'])
        self.assertEqual(saved, a.checkpoint())
        resumed = load().World.restore(saved, 'weather-tests')
        a.step(555); resumed.step(555)
        self.assertEqual(a.checkpoint(), resumed.checkpoint())

    def test_fresh_process_resume(self):
        import tempfile
        w = self.world(); w.step(975)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'state.txt'
            checkpoint.write_text(w.checkpoint(), encoding='utf8')
            code = "from pathlib import Path;from underworld.weather_runtime import load;import sys;w=load().World.restore(Path(sys.argv[1]).read_text(encoding='utf8'),'weather-tests');w.step(777);print(w.checkpoint())"
            result = subprocess.check_output([sys.executable, '-c', code, str(checkpoint)], text=True)
        w.step(777)
        self.assertEqual(w.checkpoint(), result.removesuffix('\n'))

    def test_season_boundary_and_long_calendar(self):
        w = self.world(dt=.25)
        w.step(2399); before = w.weather_snapshot()
        w.step(1); after = w.weather_snapshot()
        self.assertEqual(after['season'], 'summer')
        self.assertLess(abs(before['ambient_c']-after['ambient_c']), .01)
        for _ in range(10):w.step(10000)
        self.assertEqual(w.weather_snapshot()['year_index'], '10')
        self.assertEqual(w.weather_snapshot()['day_s'], 86400)
        self.assertTrue(w.snapshot()['sunlight_w_m2'] >= 0)

    def test_disabled_native_matches_old_runtime_bodies_and_resources(self):
        code = "from underworld.native import load_native;import json;w=load_native().World(seed=53,population=1,width=32,height=32,dt=.1,scripted=False,bodies=True,run_id='weather-tests');w.step(1000);print(json.dumps(w.snapshot()))"
        env = os.environ | {'UNDERWORLD_BUILD': str(Path('build/living-d').resolve())}
        old = json.loads(subprocess.check_output([sys.executable, '-c', code], env=env, text=True))
        w = self.world(enabled=False, bodies=True); w.step(1000)
        new = json.loads(json.dumps(w.snapshot()))
        for key in ('entities', 'material_totals_ug', 'sunlight_w_m2', 'simulated_time_s', 'event_counts'):
            self.assertEqual(new[key], old[key], key)
        with self.assertRaises(ValueError):
            load().World.restore('UW9 old-build previous=UW8', 'test')

    def test_weather_changes_actual_solar_ledger_and_batching_is_invariant(self):
        enabled, disabled = self.world(), self.world(enabled=False)
        enabled.step(1500); disabled.step(1500)
        self.assertLess(enabled.snapshot()['solar_input_j'], disabled.snapshot()['solar_input_j'])
        self.assertEqual(enabled.snapshot()['solar_input_j'], enabled.snapshot()['environment_energy_j'])
        a, b = self.world(dt=.25), self.world(dt=.25)
        a.step(10000)
        for _ in range(100):b.step(100)
        self.assertEqual(a.checkpoint(), b.checkpoint())

    def test_declared_profiles_and_tampered_climate_refusal(self):
        from underworld.weather_runtime import configuration
        self.assertEqual(configuration('config/weather-normal.toml')['year_s'], 31557600)
        self.assertEqual(configuration('config/weather-research.toml')['year_s'], 2400)
        w = self.world()
        checkpoint = w.checkpoint()
        broken = checkpoint.replace('WEATHER1 1 2400 ', 'WEATHER1 1 -2400 ')
        self.assertNotEqual(checkpoint, broken)
        with self.assertRaises(ValueError):load().World.restore(broken, 'weather-tests')


if __name__ == '__main__':unittest.main()
