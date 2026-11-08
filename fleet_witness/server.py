"""Loopback replay server with an explicit, read-only four-file surface."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import stat
from urllib.parse import unquote, urlsplit

ASSETS = {'index.html': 'text/html; charset=utf-8',
          'styles.css': 'text/css; charset=utf-8',
          'app.js': 'text/javascript; charset=utf-8',
          'replay.json': 'application/json; charset=utf-8'}
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
       "img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")


class ReplayServer(ThreadingHTTPServer):
    def __init__(self, directory: Path, port: int):
        # Anchor requests to this directory descriptor, even if its name changes.
        self.root_fd = os.open(Path(directory).resolve(strict=True), os.O_RDONLY | os.O_DIRECTORY)
        try:
            super().__init__(('127.0.0.1', port), ReplayHandler)
        except BaseException:
            os.close(self.root_fd)
            raise

    def server_close(self):
        super().server_close()
        if self.root_fd is not None:
            os.close(self.root_fd)
            self.root_fd = None


class ReplayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _respond(self, status, body=b'', content_type='text/plain; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        if status == 405:
            self.send_header('Allow', 'GET, HEAD')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        try:
            path = unquote(urlsplit(self.path).path, errors='strict')
        except (ValueError, UnicodeError):
            return self._respond(404, b'Not found\n')
        name = 'index.html' if path == '/' else path.removeprefix('/')
        if path != '/' and path != '/' + name or name not in ASSETS:
            return self._respond(404, b'Not found\n')
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.server.root_fd)
            with os.fdopen(descriptor, 'rb') as handle:
                if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                    return self._respond(404, b'Not found\n')
                body = handle.read()
        except OSError:
            return self._respond(404, b'Not found\n')
        self._respond(200, body, ASSETS[name])

    do_HEAD = do_GET

    def _deny_write(self):
        self._respond(405, b'Read-only replay server\n')

    do_POST = do_PUT = do_PATCH = do_DELETE = _deny_write


def create_server(directory: Path, port: int = 8765) -> ReplayServer:
    """Construct a loopback server; caller owns shutdown and server_close."""
    return ReplayServer(directory, port)


def serve(directory: Path, port: int = 8765):
    with create_server(directory, port) as server:
        print(f'Fleet Witness scripted replay: http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
