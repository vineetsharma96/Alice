import tempfile
import time
from pathlib import Path
from unittest import TestCase
from underworld import life_store as store
from underworld.life_control import Control


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
