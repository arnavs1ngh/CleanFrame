"""Serve the actual TV UI and the retained design gallery on this Mac."""
import argparse
import io
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit, parse_qs
from font_assets import font_overlay

ROOT = Path(__file__).resolve().parents[1]

# Preview-only Home Assistant mock. Activated by ?ha=ok|fail|slow on the preview URL.
# This never touches app/ and is never part of the packaged widget; scripts/check.py
# greps app/ for these exact markers to guard against that.
HA_MOCK_SCRIPT = '''<script>/* HA-PREVIEW-MOCK: dev-only, never packaged. */
(function () {
  var mode = new URLSearchParams(location.search).get('ha');
  if (!mode) return;
  window.HA_CONFIG = { base: 'http://mock.local:8123', actions: {
    lightsOn: 'mock-lights-on', lightsOff: 'mock-lights-off',
    jellyfinSyncOn: 'mock-jellyfin-on', jellyfinSyncOff: 'mock-jellyfin-off'
  } };
  function FakeXHR() {}
  FakeXHR.prototype.open = function (method, url) { this._url = url; };
  FakeXHR.prototype.setRequestHeader = function () {};
  FakeXHR.prototype.send = function () {
    var self = this;
    if (String(this._url).indexOf('/api/webhook/') < 0) return;
    if (mode === 'slow') return; // never resolves; ha.js's own 4s bounded() timeout wins
    setTimeout(function () {
      if (mode === 'fail') { self.status = 0; if (self.onerror) self.onerror(); }
      else { self.status = 200; if (self.onload) self.onload(); }
    }, 300);
  };
  window.XMLHttpRequest = FakeXHR;
  window.addEventListener('DOMContentLoaded', function () {
    var b = document.createElement('div');
    b.textContent = 'HA mock: ' + mode;
    b.style.cssText = 'position:fixed;left:16px;bottom:16px;z-index:999999;background:#e0433d;' +
      'color:#fff;font:600 20px/1.4 -apple-system,sans-serif;padding:8px 16px;border-radius:10px;' +
      'box-shadow:0 4px 16px rgba(0,0,0,.4);pointer-events:none';
    document.body.appendChild(b);
  });
}());
</script>
'''


class PreviewServer(ThreadingHTTPServer):
    request_queue_size = 128


class Preview(SimpleHTTPRequestHandler):
    def send_head(self):
        split = urlsplit(self.path)
        route = unquote(split.path)
        if route in ('/home', '/home/') and parse_qs(split.query).get('ha'):
            html = (ROOT / 'app/index.html').read_text()
            marker = '<script src="ha.js"></script>'
            if marker in html:
                html = html.replace(marker, HA_MOCK_SCRIPT + marker)
            content = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
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
        if urlsplit(self.path).path == '/':
            self.send_response(302)
            self.send_header('Location', '/home/')
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4795)
    parser.add_argument('--public-fonts', action='store_true', help='Use only the fonts distributed with the source')
    args = parser.parse_args()
    server = PreviewServer(('127.0.0.1', args.port), Preview)
    server.include_private_fonts = not args.public_fonts
    print('CleanFrame preview: http://127.0.0.1:' + str(server.server_port) + '/home/', flush=True)
    server.serve_forever()
