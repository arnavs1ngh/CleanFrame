"""Restores every app in a plan.py baseline to its originally-recorded app_disable value
(pkgcmd -A for anything that should go back to enabled), independently re-verified against
package_app_info.app_disable afterwards.

Usage: python3 scripts/debloat/restore.py <baseline.json path>
Writes .local/debloat/plan/<name>/restore-result.json alongside the baseline.
"""
from pathlib import Path
import json, re, sys
import transport

if len(sys.argv) != 2:
    raise SystemExit('Usage: restore.py <baseline.json path>')
baseline_path = Path(sys.argv[1])
baseline = json.loads(baseline_path.read_text())
out_dir = baseline_path.parent

to_enable = [aid for aid, v in baseline['apps'].items() if v['app_disable'] == 'false']
if not to_enable:
    print('Nothing to restore - every app in this baseline started disabled.')
    raise SystemExit(0)

enable_lines = '\n'.join('pkgcmd -A -t app -n \'{0}\' --global 2>&1'.format(aid.replace("'", "'\\''")) for aid in to_enable)
id_list_sql = ','.join("'" + aid.replace("'", "''") + "'" for aid in to_enable)
script = (
    "set -u\n"
    "printf 'CLEANFRAME_DEBLOAT_BEGIN\\n'\n"
    "printf 'RESTORING %s apps\\n'\n"
    + enable_lines + "\n"
    "printf 'VERIFY\\n'\n"
    "sqlite3 /opt/dbspace/.pkgmgr_parser.db "
    "\"SELECT app_id||'|'||app_disable||'|'||app_onboot||'|'||app_autorestart "
    "FROM package_app_info WHERE app_id IN (" + id_list_sql + ");\"\n"
    "printf 'CLEANFRAME_DEBLOAT_END\\n'\n"
).replace('%s', str(len(to_enable)))

output = transport.run_script(script, label='restore-' + out_dir.name)
(out_dir / 'restore-raw-output.txt').write_text(output)

verify = {}
for line in output.splitlines():
    m = re.match(r'^([^\|]+)\|(true|false)\|(true|false)\|(true|false)$', line.strip())
    if m:
        verify[m.group(1)] = {'app_disable': m.group(2), 'app_onboot': m.group(3), 'app_autorestart': m.group(4)}

ok, failed = [], []
for aid in to_enable:
    v = verify.get(aid)
    before = baseline['apps'][aid]
    if v is None:
        failed.append({'id': aid, 'reason': 'no verify row returned'})
    elif v != before:
        failed.append({'id': aid, 'reason': 'mismatch, now ' + json.dumps(v) + ' expected ' + json.dumps(before)})
    else:
        ok.append(aid)

result = {'restored_to_enabled': to_enable, 'ok': ok, 'failed': failed}
(out_dir / 'restore-result.json').write_text(json.dumps(result, indent=2) + '\n')

print(len(ok), 'of', len(to_enable), 'restored and verified to exact original values.')
if failed:
    print('FAILED - investigate before trusting this restore is complete:')
    for f in failed:
        print(' ', f['id'], '-', f['reason'])
    raise SystemExit(1)
