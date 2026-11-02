"""Read-only. Builds the exact-value recovery baseline for a set of candidate apps from
profiles.json, by querying their real current package_app_info row (not just presence, like
snapshot.py - the actual app_disable/app_onboot/app_autorestart values apply.py/restore.py need).

Usage: python3 scripts/debloat/plan.py [group ...]   # omit groups for all of them
Writes .local/debloat/plan/<name>/baseline.json, where <name> is a timestamp.
"""
from pathlib import Path
import json, re, sys, time
import transport

ROOT = Path(__file__).resolve().parents[2]
PROFILES = json.loads((ROOT / 'scripts/debloat/profiles.json').read_text())

requested_groups = sys.argv[1:] or [k for k in PROFILES if k != '_comment']
for g in requested_groups:
    if g not in PROFILES or g == '_comment':
        raise SystemExit('Unknown group: ' + g)

app_ids = []
for g in requested_groups:
    for app in PROFILES[g]['apps']:
        app_ids.append(app['id'])

if not app_ids:
    raise SystemExit('No candidate apps in the requested group(s).')

id_list_sql = ','.join("'" + aid.replace("'", "''") + "'" for aid in app_ids)
script = (
    "set -u\n"
    "printf 'CLEANFRAME_DEBLOAT_BEGIN\\n'\n"
    "sqlite3 /opt/dbspace/.pkgmgr_parser.db "
    "\"SELECT app_id||'|'||app_disable||'|'||app_onboot||'|'||app_autorestart "
    "FROM package_app_info WHERE app_id IN (" + id_list_sql + ");\"\n"
    "printf 'CLEANFRAME_DEBLOAT_END\\n'\n"
)

name = time.strftime('%Y%m%d-%H%M%S')
out_dir = ROOT / '.local/debloat/plan' / name
out_dir.mkdir(parents=True, exist_ok=True)

output = transport.run_script(script, label='plan-' + name)
rows = {}
for line in output.splitlines():
    m = re.match(r'^([^\|]+)\|(true|false)\|(true|false)\|(true|false)$', line.strip())
    if m:
        rows[m.group(1)] = {'app_disable': m.group(2), 'app_onboot': m.group(3), 'app_autorestart': m.group(4)}

missing = [aid for aid in app_ids if aid not in rows]
baseline = {
    'captured_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'groups': requested_groups,
    'apps': rows,
    'missing': missing,
}
(out_dir / 'baseline.json').write_text(json.dumps(baseline, indent=2) + '\n')

print('Baseline captured for', len(rows), 'of', len(app_ids), 'requested apps ->', out_dir / 'baseline.json')
if missing:
    print('NOT FOUND (not in package_app_info, skipped):')
    for aid in missing:
        print(' ', aid)
already_disabled = [aid for aid, v in rows.items() if v['app_disable'] == 'true']
if already_disabled:
    print('Already disabled before this plan (left alone by apply.py, not touched):')
    for aid in already_disabled:
        print(' ', aid)
