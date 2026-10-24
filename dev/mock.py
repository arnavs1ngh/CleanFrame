"""DEV-ONLY mock of the house-api backend, used by scripts/preview.py.

Never imported by anything under app/, never packaged. Serves canned
responses from dev/fixtures/v1/ so the UI can be built before house-api
exists. Supports the delay/fail test knobs and ETag/If-None-Match -> 304,
and keeps a tiny in-memory override so POSTed toggle actions stick for
subsequent GETs within the same preview process.
"""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'dev/fixtures/v1'

_overrides = {}  # (scenario, tile_id) -> dict of field overrides, reset when the preview process restarts


def _load_fixture(scenario):
    path = FIXTURES / (scenario + '.json')
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _apply_overrides(scenario, data):
    tiles = data.get('tiles', {}).get('data')
    if isinstance(tiles, list):
        for tile in tiles:
            key = (scenario, tile.get('id'))
            if key in _overrides:
                tile.update(_overrides[key])
    return data


def _etag(body):
    return '"' + hashlib.sha1(body).hexdigest() + '"'


def _knobs(query):
    try:
        delay_ms = max(0, int(query.get('delay', ['0'])[0]))
    except ValueError:
        delay_ms = 0
    return delay_ms, query.get('fail', ['0'])[0] == '1'


def _send_json(handler, status, payload, extra_headers=None):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    for name, value in (extra_headers or {}).items():
        handler.send_header(name, value)
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    if handler.command != 'HEAD':
        handler.wfile.write(body)


def handle_get_home(handler, query):
    """GET /mock/v1/home?scenario=<name>&delay=<ms>&fail=<0|1>"""
    scenario = query.get('scenario', ['normal'])[0]
    delay_ms, fail = _knobs(query)
    if delay_ms:
        time.sleep(delay_ms / 1000.0)
    if fail:
        _send_json(handler, 500, {'error': 'mock: forced failure'})
        return
    data = _load_fixture(scenario)
    if data is None:
        _send_json(handler, 404, {'error': 'Unknown scenario: ' + scenario})
        return
    data = _apply_overrides(scenario, data)
    body = json.dumps(data).encode()
    etag = _etag(body)
    if handler.headers.get('If-None-Match') == etag:
        handler.send_response(304)
        handler.send_header('ETag', etag)
        handler.end_headers()
        return
    handler.send_response(200)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('ETag', etag)
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


ADJUSTABLE_FIELDS = ('brightness', 'color_mode', 'rgb', 'color_temp_k')


def handle_post_action(handler, tile_id, query, body):
    """POST /mock/v1/actions/{id}?scenario=<name>&delay=<ms>&fail=<0|1>

    body is the parsed JSON request body (or {} for a plain fire-and-forget
    toggle/scene/button press): {"brightness": 72} / {"color_temp_k": 3200} /
    {"rgb": {"r": 255, "g": 120, "b": 80}, "color_mode": "color"}.
    """
    scenario = query.get('scenario', ['normal'])[0]
    delay_ms, fail = _knobs(query)
    if delay_ms:
        time.sleep(delay_ms / 1000.0)
    data = _load_fixture(scenario)
    tiles = (data or {}).get('tiles', {}).get('data') or []
    tile = next((t for t in tiles if t.get('id') == tile_id), None)
    if tile is None:
        _send_json(handler, 404, {'error': 'Unknown tile: ' + tile_id})
        return
    tile = dict(tile)
    key = (scenario, tile_id)
    if key in _overrides:
        tile.update(_overrides[key])
    if fail:
        _send_json(handler, 200, {'ok': False, 'tile': tile})
        return
    changes = {k: v for k, v in (body or {}).items() if k in ADJUSTABLE_FIELDS}
    if changes:
        tile.update(changes)
    elif tile.get('kind') == 'toggle':
        changes = {'state': 'off' if tile.get('state') == 'on' else 'on'}
        tile.update(changes)
    _overrides.setdefault(key, {}).update(changes)
    _send_json(handler, 200, {'ok': True, 'tile': tile})
