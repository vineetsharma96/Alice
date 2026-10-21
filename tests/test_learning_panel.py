import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from underworld import composition as comp, learning_panel, storage


class LearningPanelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'panel.sqlite'
        comp.initialize(self.path)

    def test_projection_and_http_are_read_only_and_bounded(self):
        before = comp.audit(self.path)
        head = storage.inspect(self.path)['state_hash']
        with learning_panel.server(self.path, 0) as app:
            worker = threading.Thread(target=app.serve_forever, daemon=True)
            worker.start()
            try:
                url = f'http://127.0.0.1:{app.server_port}'
                with urlopen(url + '/api/learning') as response:
                    packet = json.load(response)
                    self.assertIn("default-src 'self'", response.headers['Content-Security-Policy'])
                self.assertTrue(packet['operator_only'])
                self.assertTrue(packet['read_only'])
                self.assertEqual(len(packet['people']), 4)
                self.assertTrue(all(len(p['recent_records']) <= 64 for p in packet['people'].values()))
                for path in ('/', '/panel.css', '/panel.js'):
                    with urlopen(url + path) as response:
                        self.assertEqual(response.status, 200)
                for path in ('/../../.env', '/api/control'):
                    with self.assertRaises(HTTPError) as error:
                        urlopen(url + path)
                    self.assertEqual(error.exception.code, 404)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url + '/api/learning', data=b'{}', method='POST'))
                self.assertEqual(error.exception.code, 501)
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url + '/', headers={'Host': 'untrusted.example'}))
                self.assertEqual(error.exception.code, 403)
            finally:
                app.shutdown()
                worker.join(3)
        self.assertEqual(comp.audit(self.path), before)
        self.assertEqual(storage.inspect(self.path)['state_hash'], head)


if __name__ == '__main__':
    unittest.main()
