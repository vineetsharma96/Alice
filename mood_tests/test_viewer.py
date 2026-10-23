import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from underworld import mood_store as store,weather_store as weather
from underworld.mood_viewer import server


class ViewerTests(unittest.TestCase):
    def test_actual_mood_panel_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'w.sqlite';path=Path(td)/'m.sqlite'
            weather.initialize(src,population=1);store.attach(src,path)
            store.commit(path,dict(kind='step',ticks=40),'one')
            before=store.inspect(path);http=server(path,0)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{http.server_port}'
                for route in ('/','/mood-panel.js','/weather.js','/vendor/three.core.min.js','/api/mood'):
                    with urlopen(base+route) as r:
                        self.assertEqual(r.status,200)
                        if route=='/api/mood':self.assertTrue(json.load(r)['read_only'])
                for request in (Request(base+'/api/mood',data=b'{}',method='POST'),base+'/api/mood?agent=agent-99'):
                    with self.assertRaises(HTTPError):urlopen(request)
                self.assertEqual(before,store.inspect(path))
            finally:http.shutdown();http.server_close();thread.join()


if __name__=='__main__':unittest.main()
