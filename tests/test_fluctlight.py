import unittest

from underworld.fluctlight import calendar, new_profile, observe, projected_lifespan_days, teach, advance


class FluctlightTests(unittest.TestCase):
    def observation(self, agent):
        return {
            'agent_id': agent, 'tick': '12',
            'own_state': {'position_m': (2.0, 3.0)},
            'visible_entities': [
                {'entity_id': 'tree-1', 'kind': 'tree', 'position_m': (2.0, 8.0), 'stage': 'mature', 'mass_ug': '800000000'},
                {'entity_id': 'stone-1', 'kind': 'stone', 'position_m': (3.0, 3.0), 'mass_ug': '300000000'},
                {'entity_id': 'agent-2', 'kind': 'actor', 'position_m': (2.0, 3.0), 'body': {'hunger': .9}},
            ],
        }

    def test_observation_is_private_and_teaching_is_provenance_bounded(self):
        teacher = observe(new_profile('teacher', role='teacher'), self.observation('teacher'))
        learner = new_profile('learner')
        taught, learned = teach(teacher, learner, evidence_ids=['tree-1'])
        self.assertEqual(learned['knowledge']['lessons']['survival_basics']['teacher'], 'teacher')
        self.assertEqual(taught['teaching']['lessons_given'], 1)
        self.assertNotIn('agent-2', teacher['knowledge']['known_locations'])

    def test_lifespans_teacher_short_and_health_adjusted(self):
        teacher = new_profile('teacher', role='teacher')
        person = new_profile('person', seed=5, health=.5)
        self.assertEqual(projected_lifespan_days(teacher), 7.0)
        self.assertGreater(projected_lifespan_days(person), 0)
        self.assertFalse(advance(teacher, 7 * 86400)['alive'])
        self.assertTrue(advance(person, 1)['alive'])

    def test_calendar_has_months_sun_moon_ellipse_and_eclipse_windows(self):
        result = calendar(15 * 86400)
        self.assertEqual(result['month_number'], 1)
        self.assertIn('elevation_deg', result['sun'])
        self.assertIn(result['moon']['phase'], {'new', 'waxing_crescent', 'first_quarter', 'waxing_gibbous', 'full', 'waning_gibbous', 'third_quarter', 'waning_crescent'})
        self.assertGreater(result['orbit']['eccentricity'], 0)
        self.assertIn('solar_possible', result['eclipse_window'])


if __name__ == '__main__':
    unittest.main()
