"""Check that the widget manifest and its referenced files are present."""
from pathlib import Path
import json
import xml.etree.ElementTree as XML
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from font_assets import is_runtime_source

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
        if reference == 'ha-config.js':
            continue  # Private, gitignored and optional; a missing file must not break the app.
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
print('Widget identity, version and bundled resources are valid.')
