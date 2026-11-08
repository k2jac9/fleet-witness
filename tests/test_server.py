import http.client
from pathlib import Path
import tempfile
import threading
import unittest

try:
    from fleet_witness.server import create_server
except ImportError:
    create_server = None


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(create_server, 'read-only server has not been implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, content in {'index.html': '<html>fixture</html>', 'app.js': '"use strict";',
                'styles.css': 'body {}', 'replay.json': '{"schema_version":"1.0"}',
                'witness.sqlite3': 'PRIVATE DATABASE'}.items():
            (self.root / name).write_text(content)
        (self.root / 'nested').mkdir()
        (self.root / 'nested/secret').write_text('PRIVATE NESTED')
        self.server = create_server(self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, method, path):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        connection.request(method, path)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_loopback_binding_and_allowlisted_content_types(self):
        self.assertEqual(self.server.server_address[0], '127.0.0.1')
        for path, content_type in [('/', 'text/html'), ('/index.html', 'text/html'),
                ('/styles.css', 'text/css'), ('/app.js', 'text/javascript'), ('/replay.json', 'application/json')]:
            with self.subTest(path=path):
                status, headers, body = self.request('GET', path)
                self.assertEqual(status, 200)
                self.assertTrue(headers['Content-Type'].startswith(content_type))
                self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertTrue(body)
        status, _, body = self.request('HEAD', '/replay.json')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')

    def test_unlisted_traversal_and_directories_are_denied(self):
        for path in ['/witness.sqlite3', '/nested/', '/nested/secret', '/../index.html',
                     '/%2e%2e/index.html', '/%2e%2e%2fwitness.sqlite3', '/app.js/extra', '/.env']:
            with self.subTest(path=path):
                status, _, body = self.request('GET', path)
                self.assertEqual(status, 404)
                self.assertNotIn(b'PRIVATE', body)

    def test_allowlisted_symlink_cannot_expose_another_file(self):
        (self.root / 'app.js').unlink()
        (self.root / 'app.js').symlink_to(self.root / 'witness.sqlite3')
        self.assertEqual(self.request('GET', '/app.js')[0], 404)

    def test_writes_are_denied(self):
        for method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            self.assertEqual(self.request(method, '/replay.json')[0], 405)
        self.assertEqual((self.root / 'replay.json').read_text(), '{"schema_version":"1.0"}')
