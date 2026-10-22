import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from underworld import emotion_store as store,weather_store as weather
from underworld.emotion_viewer import server


class ViewerTests(unittest.TestCase):
    def test_readonly_existing_scene_private_panel_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source.sqlite';live=Path(tmp)/'live.sqlite'
            weather.initialize(src,population=1);store.attach(src,live)
            store.commit(live,dict(kind='emotion-policy',agent='agent-1'),'first')
            before=store.inspect(live);http=server(live,0)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{http.server_port}'
                for route in ('/','/emotion-panel.js','/weather.js','/vendor/three.core.min.js','/api/weather','/api/emotion'):
                    with urlopen(base+route) as response:
                        self.assertEqual(response.status,200)
                        self.assertIn('Content-Security-Policy',response.headers)
                        if route=='/api/emotion':
                            data=json.load(response);self.assertEqual(data['person']['owner'],'agent-1')
                            self.assertTrue(data['read_only'])
                for request in (Request(base+'/api/emotion',data=b'{}',method='POST'),base+'/api/emotion?agent=agent-2',base+'/../HANDOFF.md'):
                    with self.assertRaises(HTTPError):urlopen(request)
                self.assertEqual(before,store.inspect(live))
            finally:http.shutdown();http.server_close();thread.join()


if __name__=='__main__':unittest.main()
