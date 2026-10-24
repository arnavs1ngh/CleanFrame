"""Check that the widget manifest and its referenced files are present."""
from pathlib import Path
import json
import xml.etree.ElementTree as XML
import re
import sys
import tempfile
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from font_assets import is_runtime_source, write_widget_archive

root = Path(__file__).resolve().parents[1]
app = root / 'app'
manifest = XML.parse(app / 'config.xml').getroot()
ns = {'w': 'http://www.w3.org/ns/widgets', 't': 'http://tizen.org/ns/widgets'}
identity = manifest.find('t:application', ns)
assert identity is not None, 'Missing application identity'
assert identity.get('package') == 'MaytonHome', 'Keep the installed package identity stable'
assert identity.get('id') == 'MaytonHome.Home', 'Keep the installed application ID stable'
assert manifest.get('version') == json.loads((root / 'package.json').read_text())['version'], 'Manifest/package versions differ'
for tag in ['content', 'icon']:
    node = manifest.find('w:' + tag, ns)
    assert node is not None and (app / node.get('src', '')).is_file(), 'Missing ' + tag + ' file'
assert all((app / name).is_file() for name in ['main.js', 'style.css'])
for reference in ['assets/wallpapers/catalog.js', 'assets/adaptive-ink.js', 'assets/font-catalog.js']:
    assert (app / reference).is_file(), 'Missing runtime catalogue: ' + reference
for filename in ['index.html']:
    source = (app / filename).read_text()
    pattern = r'(?:src|href)=[\"\']([^\"\']+)' if filename.endswith('.html') else r'from\s+[\"\']([^\"\']+)'
    for reference in re.findall(pattern, source):
        if ':' in reference or reference.startswith('$'):
            continue
        # Pre-wiring only: house-api doesn't exist yet, so house-api-config.js stays gitignored
        # and optional - its absence must hide the house features, not fail the check.
        if reference == 'house-api-config.js' and not (app / reference).is_file():
            continue
        assert (app / reference).is_file(), 'Missing bundled resource: ' + reference
        if filename.endswith('.js'):
            assert reference.startswith(('./', '../')), 'Module imports must be relative paths'
for css in app.rglob('*.css'):
    for reference in re.findall(r'url\([\"\']?([^\)\"\']+)', css.read_text()):
        if ':' not in reference:
            assert (css.parent / reference.split('?')[0]).is_file(), 'Missing CSS resource: ' + reference
# These resource names are constructed at runtime, so HTML/CSS reference checks cannot find them.
walls = json.loads((app / 'assets/wallpapers/SOURCES.json').read_text())
for wall in walls:
    for field in ['src', 'thumb']:
        assert (app / wall[field]).is_file(), 'Missing wallpaper: ' + wall[field]
    wall_id = wall['id']
    for suffix in ['study-soft', 'field-blur', 'field-frost', 'field-clear']:
        assert (app / ('assets/materials/' + wall_id + '-' + suffix + '.jpg')).is_file(), 'Missing registered material: ' + wall_id + '/' + suffix
    assert (app / ('assets/wallpapers/' + wall_id + '-panel.jpg')).is_file(), 'Missing panel backdrop: ' + wall_id
for icon in ['netflix', 'youtube', 'primevideo', 'spotify', 'jellyfin', 'bbc', 'itvx', 'channel4', 'art', 'apps', 'settings', 'bulb']:
    assert (app / ('assets/icons/' + icon + '.svg')).is_file(), 'Missing icon: ' + icon

# Home Assistant: the example config is a template only and must stay out of the packaged widget.
assert (app / 'ha-config.example.js').is_file(), 'Missing app/ha-config.example.js template'
assert not is_runtime_source('ha-config.example.js'), 'ha-config.example.js must be excluded from the packaged widget'
# Wiring is live: ha-config.js is now required (caught above via the index.html reference scan,
# since it's no longer exempted), config.xml must declare internet + a scoped (non-wildcard)
# access origin, and it must match ha-config.js's own base - not some other host.
manifest_text = (app / 'config.xml').read_text()
assert 'http://tizen.org/privilege/internet' in manifest_text, 'Missing internet privilege for Home Assistant'
access_match = re.search(r'<access\s+origin="([^"]+)"\s+subdomains="(true|false)"', manifest_text)
assert access_match, 'Missing scoped <access> entry for Home Assistant'
assert access_match.group(1) not in ('*', ''), 'Access origin must be scoped, not wildcarded'
assert access_match.group(2) == 'false', 'Access origin should not blanket-allow subdomains'
ha_config_text = (app / 'ha-config.js').read_text()
base_match = re.search(r'base\s*:\s*[\'"]([^\'"]+)[\'"]', ha_config_text)
assert base_match and base_match.group(1).startswith(access_match.group(1)), 'config.xml access origin does not match ha-config.js base'

# house-api: pre-wiring dev tooling only. The example config is a template and must
# stay out of the packaged widget; dev/ (mock server, fixtures) lives outside app/ and
# must never end up in a built widget either.
assert (app / 'house-api-config.example.js').is_file(), 'Missing app/house-api-config.example.js template'
assert not is_runtime_source('house-api-config.example.js'), 'house-api-config.example.js must be excluded from the packaged widget'
with tempfile.TemporaryDirectory() as tmp:
    dry_run = Path(tmp) / 'check-dry-run.wgt'
    write_widget_archive(dry_run, include_private=False)
    with zipfile.ZipFile(dry_run) as archive:
        names = archive.namelist()
assert not any(name.startswith('dev/') for name in names), 'dev/ (mock server, fixtures) must not be packaged'
assert not any('mock' in name.lower() for name in names), 'Mock code must not be packaged'
assert 'house-api-config.example.js' not in names, 'house-api-config.example.js must not be packaged'
print('Widget identity, version and bundled resources are valid.')
