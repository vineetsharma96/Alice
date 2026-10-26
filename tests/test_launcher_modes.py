import sys
from unittest import TestCase
from unittest.mock import patch

from underworld import app


class LauncherModeTests(TestCase):
    def test_control_flag_delegates_to_integrated_control_main(self):
        original = sys.argv[:]
        try:
            with patch('underworld.life_control.main', return_value=7) as delegated:
                self.assertEqual(app.main(['--control', '--db', 'data/world.sqlite']), 7)
                delegated.assert_called_once_with()
                self.assertEqual(sys.argv[1:], ['--db', 'data/world.sqlite'])
        finally:
            sys.argv[:] = original

    def test_readonly_flag_delegates_to_integrated_viewer_main(self):
        original = sys.argv[:]
        try:
            with patch('underworld.life_viewer.main', return_value=3) as delegated:
                self.assertEqual(app.main(['--readonly', '--db', 'data/world.sqlite']), 3)
                delegated.assert_called_once_with()
                self.assertEqual(sys.argv[1:], ['--db', 'data/world.sqlite'])
        finally:
            sys.argv[:] = original

    def test_word_aliases_delegate_to_the_same_modes(self):
        original = sys.argv[:]
        try:
            with patch('underworld.life_control.main', return_value=7) as control_main:
                self.assertEqual(app.main(['control', '--db', 'data/world.sqlite']), 7)
                control_main.assert_called_once_with()
            with patch('underworld.life_viewer.main', return_value=3) as viewer_main:
                self.assertEqual(app.main(['readonly', '--db', 'data/world.sqlite']), 3)
                viewer_main.assert_called_once_with()
        finally:
            sys.argv[:] = original
