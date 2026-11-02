"""Disables every app in a plan.py baseline that isn't already disabled, using the mechanism
proven in docs/debloat.md ("What's proven"): pkgcmd -D -t app -n <id> --global, independently
re-verified against package_app_info.app_disable afterwards - not just trusting pkgcmd's own
"val[ok]" line.

Usage: python3 scripts/debloat/apply.py <baseline.json path>
Writes .local/debloat/plan/<name>/apply-result.json alongside the baseline.
Stops (does not apply anything further) if a prior app's verification doesn't match expected.
"""
from pathlib import Path
import json, re, sys
import transport

if len(sys.argv) != 2:
    raise SystemExit('Usage: apply.py <baseline.json path>')
baseline_path = Path(sys.argv[1])
baseline = json.loads(baseline_path.read_text())
out_dir = baseline_path.parent
all_ids = list(baseline['apps'].keys())

# Live check, not the baseline file's recorded values - the baseline is a point-in-time capture
# and may now be stale (e.g. a prior apply.py run against a different/overlapping baseline
# already disabled some of these), so trusting it here would under/over-count "already disabled".
live_id_list_sql = ','.join("'" + aid.replace("'", "''") + "'" for aid in all_ids)
live_script = (
    "set -u\n"
    "printf 'CLEANFRAME_DEBLOAT_BEGIN\\n'\n"
    "sqlite3 /opt/dbspace/.pkgmgr_parser.db "
    "\"SELECT app_id||'|'||app_disable FROM package_app_info WHERE app_id IN (" + live_id_list_sql + ");\"\n"
    "printf 'CLEANFRAME_DEBLOAT_END\\n'\n"
)
live_output = transport.run_script(live_script, label='apply-precheck-' + out_dir.name)
live_disabled = set()
for line in live_output.splitlines():
    m = re.match(r'^([^\|]+)\|(true|false)$', line.strip())
    if m and m.group(2) == 'true':
        live_disabled.add(m.group(1))

targets = [aid for aid in all_ids if aid not in live_disabled]
already = [aid for aid in all_ids if aid in live_disabled]
if not targets:
    print('Nothing to do - every app in this baseline is already disabled (live check).')
    raise SystemExit(0)

disable_lines = '\n'.join('pkgcmd -D -t app -n \'{0}\' --global 2>&1'.format(aid.replace("'", "'\\''")) for aid in targets)
id_list_sql = ','.join("'" + aid.replace("'", "''") + "'" for aid in targets)
script = (
    "set -u\n"
    "printf 'CLEANFRAME_DEBLOAT_BEGIN\\n'\n"
    "printf 'APPLYING %s apps\\n'\n"
    + disable_lines + "\n"
    "printf 'VERIFY\\n'\n"
    "sqlite3 /opt/dbspace/.pkgmgr_parser.db "
    "\"SELECT app_id||'|'||app_disable||'|'||app_onboot||'|'||app_autorestart "
    "FROM package_app_info WHERE app_id IN (" + id_list_sql + ");\"\n"
    "printf 'CLEANFRAME_DEBLOAT_END\\n'\n"
).replace('%s', str(len(targets)))

output = transport.run_script(script, label='apply-' + out_dir.name)
(out_dir / 'apply-raw-output.txt').write_text(output)

verify = {}
for line in output.splitlines():
    m = re.match(r'^([^\|]+)\|(true|false)\|(true|false)\|(true|false)$', line.strip())
    if m:
        verify[m.group(1)] = {'app_disable': m.group(2), 'app_onboot': m.group(3), 'app_autorestart': m.group(4)}

ok, failed, unverifiable_onboot = [], [], []
for aid in targets:
    v = verify.get(aid)
    before = baseline['apps'][aid]
    if v is None:
        failed.append({'id': aid, 'reason': 'no verify row returned'})
        continue
    if v['app_disable'] != 'true':
        failed.append({'id': aid, 'reason': 'app_disable still ' + v['app_disable']})
        continue
    if v['app_onboot'] != before['app_onboot'] or v['app_autorestart'] != before['app_autorestart']:
        unverifiable_onboot.append(aid)
    ok.append(aid)

result = {'targets': targets, 'already_disabled_skipped': already, 'ok': ok, 'failed': failed, 'onboot_or_autorestart_changed_unexpectedly': unverifiable_onboot}
(out_dir / 'apply-result.json').write_text(json.dumps(result, indent=2) + '\n')

print(len(ok), 'of', len(targets), 'applied and verified.', len(already), 'already disabled, skipped.')
if unverifiable_onboot:
    print('WARNING - app_onboot/app_autorestart changed unexpectedly for:', unverifiable_onboot)
if failed:
    print('FAILED (left disabled where pkgcmd ran, but app_disable did not verify true - investigate before retrying):')
    for f in failed:
        print(' ', f['id'], '-', f['reason'])
    raise SystemExit(1)
