import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from underworld import memory_store as store,weather_store as weather
from underworld.memory_viewer import server


class ViewerTests(unittest.TestCase):
    def test_memory_observer_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'src';path=Path(td)/'new';weather.initialize(src,population=1)
            store.attach(src,path);store.commit(path,dict(kind='step',ticks=40),'one')
            before=store.inspect(path);http=server(path,0)
            thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{http.server_port}'
                with urlopen(base) as r:self.assertIn('memory-summary',r.read().decode())
                with urlopen(base+'/mood-panel.js') as r:self.assertIn('showMemory',r.read().decode())
                with urlopen(base+'/api/mood') as r:
                    packet=json.load(r);self.assertTrue(packet['read_only']);self.assertIn('retrieval',packet)
                with self.assertRaises(HTTPError):urlopen(Request(base+'/api/mood',data=b'{}',method='POST'))
                self.assertEqual(before,store.inspect(path))
            finally:http.shutdown();http.server_close();thread.join()


if __name__=='__main__':unittest.main()
