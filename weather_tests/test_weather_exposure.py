import unittest

from underworld.weather_runtime import climate, load


class WeatherExposureTests(unittest.TestCase):
    def world(self, cold=False, **kwargs):
        w = load().World(seed=53, population=1, width=32, height=32, dt=.25, scripted=False, bodies=True, **kwargs)
        w.configure_climate(climate(temperature_bias_c=-25 if cold else 0))
        return w

    def test_cold_rain_actual_damage_persists_and_mild_has_none(self):
        cold, mild = self.world(True), self.world()
        cold.step(600); mild.step(400)
        e = cold.weather_snapshot()['exposure']['agent-1']
        self.assertGreater(e['wetness'], .1)
        self.assertGreater(e['cold_burden'], .65)
        self.assertGreater(e['environmental_health_lost'], .03)
        self.assertLess(cold.snapshot()['entities'][4]['body']['health'], 1)
        self.assertGreater(e['environmental_fatigue_added'], 0)
        self.assertEqual(mild.weather_snapshot()['exposure']['agent-1']['environmental_health_lost'], 0)
        resumed = load().World.restore(cold.checkpoint(), 'test')
        cold.step(40); resumed.step(40)
        self.assertEqual(cold.checkpoint(), resumed.checkpoint())
        cold.check_invariants()

    def test_cold_recovers_when_season_becomes_warm_without_refilling(self):
        v = load().World(seed=53, population=1, width=32, height=32, dt=.25, scripted=False, bodies=True)
        v.configure_climate(climate(year_s=240))
        v.step(760)
        before = v.weather_snapshot()['exposure']['agent-1']['cold_burden']
        stocks = v.snapshot()['material_totals_ug']
        v.step(440)
        self.assertEqual(v.weather_snapshot()['season'], 'summer')
        self.assertGreater(before, .1)
        self.assertLess(v.weather_snapshot()['exposure']['agent-1']['cold_burden'], before / 2)
        self.assertEqual(v.snapshot()['material_totals_ug'], stocks)
        self.assertEqual(v.snapshot()['boundary_sources_ug']['food'], 0)

    def test_seasonal_growth_uses_explicit_boundary_ledger_and_zero_stays_zero(self):
        grown = self.world(tree_growth_kg_s=.001)
        static = self.world()
        grown.step(800); static.step(800)
        self.assertGreater(grown.snapshot()['boundary_sources_ug']['tree'], 0)
        self.assertLess(grown.snapshot()['boundary_sources_ug']['tree'], 200000000)
        self.assertEqual(static.snapshot()['boundary_sources_ug']['tree'], 0)
        grown.check_invariants(); static.check_invariants()

    def test_forage_regeneration_uses_seasonal_food_boundary(self):
        worlds = []
        for rate in (0, .001):
            w = load().World(seed=53, population=1, width=32, height=32, dt=.25,
                             scripted=False, bodies=True)
            w.configure_climate(climate())
            w.configure_ecology(forage_kg=0, regeneration_kg_s=rate)
            w.step(400)
            w.check_invariants()
            worlds.append(w.snapshot())
        self.assertEqual(worlds[0]['boundary_sources_ug']['food'], 0)
        self.assertGreater(worlds[1]['boundary_sources_ug']['food'], 0)
        self.assertLess(worlds[1]['boundary_sources_ug']['food'], 100000000)


if __name__ == '__main__':unittest.main()
