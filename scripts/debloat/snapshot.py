"""Read-only: capture which candidate debloat apps (scripts/debloat/profiles.json) are actually
present on the connected TV right now. Writes nothing to the device. See docs/debloat.md -
disabling anything is a separate, not-yet-built step that still needs its mechanism validated.
"""
import argparse
import datetime
import ipaddress
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--host')
parser.add_argument('--name', help='Snapshot name (default: a timestamp)')
args = parser.parse_args()
config_file = ROOT / '.local/device.json'
config = json.loads(config_file.read_text()) if config_file.exists() else {}
host = args.host or config.get('host')
if not host:
    raise SystemExit('Add the TV address to .local/device.json or pass --host.')
ipaddress.ip_address(host)
sdb = ROOT / '.local/tizen-sdk/tools/sdb'
if not sdb.exists():
    raise SystemExit('Local SDB tool missing. See docs/development.md.')
profiles = json.loads((Path(__file__).parent / 'profiles.json').read_text())
groups = {k: v for k, v in profiles.items() if not k.startswith('_')}


def run(*command, quiet=False):
    result = subprocess.run([str(sdb), *command], text=True, capture_output=True, timeout=45)
    output = result.stdout + result.stderr
    if not quiet:
        print(output, end='' if output.endswith('\n') else '\n', flush=True)
    if result.returncode:
        raise SystemExit('SDB command failed.')
    return output


serial = host + ':26101'
connected = run('connect', serial)
if 'connected to ' not in connected.lower() and 'already connected' not in connected.lower():
    raise SystemExit('TV connection was not confirmed.')

applist = run('-s', serial, 'shell', '0', 'applist', quiet=True)
pkgcmd_list = run('-s', serial, 'shell', '0', 'pkgcmd', '-l', quiet=True)

name = args.name or datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
out_dir = ROOT / '.local/debloat/snapshots' / name
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'applist.txt').write_text(applist)
(out_dir / 'pkgcmd-l.txt').write_text(pkgcmd_list)

found, missing = {}, {}
for group, spec in groups.items():
    found[group], missing[group] = [], []
    for a in spec['apps']:
        (found[group] if a['id'] in applist else missing[group]).append(a['id'])

report = {'snapshot': name, 'host': host, 'captured_at': datetime.datetime.now().isoformat(), 'found': found, 'missing': missing}
(out_dir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

print('\nSnapshot "%s" saved to %s' % (name, out_dir.relative_to(ROOT)))
for group in groups:
    print('  %s: %d/%d candidate apps present' % (group, len(found[group]), len(found[group]) + len(missing[group])))
    if missing[group]:
        print('    not found (check spelling/firmware differences): %s' % ', '.join(missing[group]))
