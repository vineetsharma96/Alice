import unittest

from underworld.weather_runtime import climate, load
from weather_tests.helpers import execute, ingredients, move, request, roof, site, walk


class WeatherShelterTests(unittest.TestCase):
    def world(self, cold=False):
        w = load().World(seed=53, population=1, width=32, height=32, dt=.25, scripted=False, bodies=True)
        w.configure_climate(climate(temperature_bias_c=-25 if cold else 0))
        return w

    def test_real_inputs_partial_restart_completion_and_repair(self):
        w = self.world(); initial = w.snapshot()['material_totals_ug']
        ingredients(w); target = site(w)
        own = w.observe_batch(['agent-1'])[0]['own_state']
        self.assertEqual(int(own['inventory_ug']['wood']), 100000000)
        self.assertEqual(int(own['inventory_ug']['fiber']), 0)
        r = request(w, 'work_construction', target, duration=12)
        self.assertEqual(w.submit(r, 'agent-1')['status'], 'accepted')
        w.step(20)
        self.assertEqual(w.weather_snapshot()['shelters'][0]['work_s'], 5)
        self.assertFalse(w.weather_snapshot()['shelters'][0]['complete'])
        resumed = load().World.restore(w.checkpoint(), 'test')
        w.step(28); resumed.step(28)
        self.assertEqual(w.checkpoint(), resumed.checkpoint())
        self.assertTrue(w.weather_snapshot()['shelters'][0]['complete'])
        w.step(40)
        before = w.weather_snapshot()['shelters'][0]['condition']
        self.assertEqual(execute(w, 'repair_shelter', target, duration=3)['status'], 'completed')
        self.assertGreater(w.weather_snapshot()['shelters'][0]['condition'], before)
        self.assertEqual(w.weather_snapshot()['shelters'][0]['mass_ug'], '1000000000')
        self.assertEqual(sum(map(int, w.snapshot()['material_totals_ug'].values())), sum(map(int, initial.values())))
        w.check_invariants()

    def test_native_coverage_edge_entry_exit_and_real_exposure_difference(self):
        w = self.world(True); target, _ = roof(w)
        exposed = load().World.restore(w.checkpoint(), 'test')
        move(w, [4, 4]); move(exposed, [1.2, 4])
        w.step(480); exposed.step(480)
        inside = w.weather_snapshot()['exposure']['agent-1']
        outside = exposed.weather_snapshot()['exposure']['agent-1']
        self.assertEqual(inside['shelter_id'], target)
        self.assertEqual(outside['shelter_id'], '')
        self.assertLess(inside['wetness'], outside['wetness'])
        self.assertLess(inside['environmental_health_lost'], outside['environmental_health_lost'])
        move(w, [4.85, 4]); w.step(1)
        self.assertEqual(w.weather_snapshot()['exposure']['agent-1']['shelter_id'], target)
        move(w, [4.86, 4]); w.step(1)
        self.assertEqual(w.weather_snapshot()['exposure']['agent-1']['shelter_id'], '')
        move(w, [6, 4]); move(w, [4, 4])
        self.assertEqual(w.weather_snapshot()['exposure']['agent-1']['shelter_id'], target)

    def test_blocked_and_missing_material_rejections_preserve_inventory(self):
        w = self.world()
        r = execute(w, 'begin_construction', parameters=dict(recipe_id='lean_to', x_m=3.4, y_m=3))
        self.assertEqual(r['error_code'], 'INSUFFICIENT_RESOURCE')
        ingredients(w)
        own = w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug']
        r = execute(w, 'begin_construction', parameters=dict(recipe_id='lean_to', x_m=2.8, y_m=4))
        self.assertEqual(r['error_code'], 'NO_PLACEMENT')
        self.assertEqual(own, w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug'])
        target = site(w)
        r = execute(w, 'cancel_construction', target)
        self.assertEqual(r['status'], 'completed')
        self.assertEqual(own, w.observe_batch(['agent-1'])[0]['own_state']['inventory_ug'])

    def test_competing_builders_do_not_duplicate_work(self):
        w = load().World(seed=53, population=2, width=32, height=32, dt=.25, scripted=False, bodies=True)
        w.configure_climate(climate())
        walk(w, [4, 2.6], 'agent-2')
        ingredients(w); target = site(w)
        first = request(w, 'work_construction', target, duration=12)
        self.assertEqual(w.submit(first, 'agent-1')['status'], 'accepted')
        second = request(w, 'work_construction', target, duration=12, agent='agent-2')
        self.assertEqual(w.submit(second, 'agent-2')['error_code'], 'TARGET_BUSY')
        w.step(48)
        self.assertEqual(w.weather_snapshot()['shelters'][0]['mass_ug'], '900000000')
        self.assertEqual(w.weather_snapshot()['shelters'][0]['work_s'], 12)
        w.check_invariants()

    def test_capacity_never_credits_fifth_occupant(self):
        w = load().World(seed=53, population=5, width=32, height=32, dt=.25, scripted=False, bodies=True)
        w.configure_climate(climate())
        for i in range(2, 6):walk(w, [8, 3+i], f'agent-{i}')
        target, _ = roof(w)
        for i, position in enumerate(([4, 4], [4.55, 4], [3.45, 4], [4, 4.55], [4, 3.45]), 1):
            walk(w, position, f'agent-{i}')
        w.step(1)
        covered = [e for e in w.weather_snapshot()['exposure'].values() if e['shelter_id'] == target]
        self.assertEqual(len(covered), 4)
        self.assertEqual(w.weather_snapshot()['exposure']['agent-5']['shelter_id'], '')
        w.check_invariants()


if __name__ == '__main__':unittest.main()
