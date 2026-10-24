"""Serve the actual TV UI and the retained design gallery on this Mac."""
import argparse
import hashlib
import io
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from font_assets import font_overlay

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dev.mock import handle_get_home, handle_post_action  # DEV-ONLY, never used by app/

LIVE_RELOAD_SCRIPT = (
    "<script>(function(){var rev=null;function poll(){"
    "var url='/dev/reload'+(rev!==null?('?since='+rev):'');"
    "fetch(url).then(function(r){return r.json();}).then(function(data){"
    "if(rev!==null&&data.rev!==rev){location.reload();return;}"
    "rev=data.rev;poll();"
    "}).catch(function(){setTimeout(poll,1000);});}"
    "poll();})();</script>"
)

# ---------- DEV-ONLY live reload: watches app/ and dev/fixtures/ for changes ----------
_watch_lock = threading.Lock()
_watch_state = {'revision': 0, 'fingerprint': ''}


def _fingerprint():
    parts = []
    for base in (ROOT / 'app', ROOT / 'dev/fixtures'):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob('*')):
            if path.is_file():
                parts.append(str(path) + ':' + str(path.stat().st_mtime_ns))
    return hashlib.sha1('\n'.join(parts).encode()).hexdigest()


def _watch_loop():
    while True:
        fp = _fingerprint()
        with _watch_lock:
            if fp != _watch_state['fingerprint']:
                _watch_state['fingerprint'] = fp
                _watch_state['revision'] += 1
        time.sleep(0.4)


class PreviewServer(ThreadingHTTPServer):
    request_queue_size = 128


class Preview(SimpleHTTPRequestHandler):
    def send_head(self):
        route = unquote(urlsplit(self.path).path)
        if route in ('/home/', '/home/index.html'):
            return self._serve_index()
        if route == '/home/house-api-config.js' and not (ROOT / 'app/house-api-config.js').is_file():
            # DEV-ONLY convenience: no real config yet, so point the preview at the mock.
            content = b"var HOUSE_API_BASE = '/mock';\n"
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            return io.BytesIO(content)
        if route in ['/home/assets/font-catalog.js', '/home/assets/private-fonts.css'] or route.startswith('/home/assets/private-fonts/'):
            source = font_overlay(include_private=self.server.include_private_fonts).get(route[len('/home/'):])
            if source is None:
                self.send_error(404, 'File not found')
                return None
            content = source.read_bytes() if isinstance(source, Path) else source
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(route))
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            return io.BytesIO(content)
        return super().send_head()

    def _serve_index(self):
        # DEV-ONLY: inject a live-reload poller into the served HTML. The file on disk is untouched.
        content = (ROOT / 'app/index.html').read_bytes()
        content = content.replace(b'</body>', LIVE_RELOAD_SCRIPT.encode() + b'</body>')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        return io.BytesIO(content)

    def translate_path(self, path):
        route = urlsplit(path).path
        # Serve only the packaged UI and offline material-builder inputs.
        if route == '/' or route == '/home':
            return str(ROOT / 'app/index.html')
        if route.startswith('/home/'):
            self.directory = str(ROOT / 'app')
            return super().translate_path(route[5:])
        if route.startswith('/build/'):
            self.directory = str(ROOT / 'scripts/materials')
            return super().translate_path(route[6:])
        self.directory = str(ROOT / 'app')
        return super().translate_path(route)

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == '/':
            self.send_response(302)
            self.send_header('Location', '/home/')
            self.end_headers()
            return
        if route == '/mock/v1/home':
            handle_get_home(self, parse_qs(urlsplit(self.path).query))
            return
        if route == '/dev/reload':
            self._handle_reload_poll(parse_qs(urlsplit(self.path).query))
            return
        super().do_GET()

    def do_POST(self):
        route = urlsplit(self.path).path
        prefix = '/mock/v1/actions/'
        if route.startswith(prefix) and len(route) > len(prefix):
            length = int(self.headers.get('Content-Length', '0') or '0')
            if length:
                self.rfile.read(length)
            handle_post_action(self, route[len(prefix):], parse_qs(urlsplit(self.path).query))
            return
        self.send_error(404, 'No such endpoint')

    def _handle_reload_poll(self, query):
        since = query.get('since', [None])[0]
        try:
            since = int(since) if since is not None else None
        except ValueError:
            since = None
        deadline = time.monotonic() + 20
        while True:
            with _watch_lock:
                rev = _watch_state['revision']
            if since is None or rev != since or time.monotonic() > deadline:
                body = ('{"rev":' + str(rev) + '}').encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            time.sleep(0.3)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        # The reload long-poll would otherwise flood the console every ~20s.
        if '/dev/reload' not in fmt % args:
            super().log_message(fmt, *args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4795)
    parser.add_argument('--public-fonts', action='store_true', help='Use only the fonts distributed with the source')
    args = parser.parse_args()
    server = PreviewServer(('127.0.0.1', args.port), Preview)
    server.include_private_fonts = not args.public_fonts
    threading.Thread(target=_watch_loop, daemon=True).start()
    print('CleanFrame preview: http://127.0.0.1:' + str(server.server_port) + '/home/', flush=True)
    server.serve_forever()
