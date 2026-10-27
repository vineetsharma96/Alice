import unittest

from underworld.time_dilation import PRESETS, SAO_NOMINAL_SCALE, get, public


class TimeDilationTests(unittest.TestCase):
    def test_sao_nominal_ratio_is_explicit_and_approximately_300_years_in_3_weeks(self):
        preset = get('sao_300y_3w')
        self.assertAlmostEqual(preset.scale, SAO_NOMINAL_SCALE)
        self.assertAlmostEqual(preset.scale * 21, 300 * 365)
        self.assertIn('does not skip native ticks', preset.warning)

    def test_presets_are_bounded_and_public(self):
        self.assertEqual(set(PRESETS), {'normal', 'fast', 'sao_300y_3w'})
        for name in PRESETS:
            value = public(name)
            self.assertEqual(value['preset'], name)
            self.assertGreater(value['scale'], 0)


if __name__ == '__main__':
    unittest.main()
