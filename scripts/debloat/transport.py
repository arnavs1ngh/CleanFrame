"""Shared transport: runs shell script source on the TV via the same reviewed package-name
command-execution workaround as scripts/native-home/run.py (see that file, its README, and
docs/debloat.md's "What's proven" section for the full explanation and validation history).

Exposes run_script(source, label) -> str, taking shell source directly (not a file path) so
plan.py/apply.py/restore.py can build one script covering many apps and execute it in a single
device round trip, rather than re-paying the injection/connection cost per app.
"""
from pathlib import Path
import base64, ipaddress, json, socket, subprocess, tempfile, time, uuid, urllib.request

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / '.local/debloat'
LOCAL.mkdir(parents=True, exist_ok=True)

BEGIN_MARK = 'CLEANFRAME_DEBLOAT_BEGIN'
END_MARK = 'CLEANFRAME_DEBLOAT_END'


def _sdb():
    host = json.loads((ROOT / '.local/device.json').read_text())['host']
    ipaddress.ip_address(host)
    with urllib.request.urlopen('http://' + host + ':8001/api/v2/', timeout=4) as response:
        info = json.load(response)
    if info.get('device', {}).get('modelName') != 'UE55CU7100KXXU':
        raise SystemExit('Model guard failed; nothing staged.')
    return str(ROOT / '.local/tizen-sdk/tools/sdb'), host + ':26101', host


def run_script(source, label='run'):
    """source: shell script text (must set -u and print BEGIN_MARK/END_MARK itself, matching
    the existing scripts/debloat/*.sh convention). label: used only for local output filenames."""
    sdb, serial, host = _sdb()

    def run(args, timeout=12):
        p = subprocess.run([sdb, *args], capture_output=True, text=True, timeout=timeout)
        if p.returncode:
            raise RuntimeError('SDB transport failed: ' + p.stdout[-300:] + p.stderr[-300:])
        return p

    run(['connect', serial])
    token = uuid.uuid4().hex[:12]
    remote = '/home/owner/share/tmp/sdk_tools/cfdb-' + token + '.sh'
    with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
        f.write(source)
        local_path = f.name
    try:
        run(['-s', serial, 'push', local_path, remote])
    finally:
        Path(local_path).unlink(missing_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect((host, 9))
        local = route.getsockname()[0]
    with socket.socket() as listener:
        listener.bind((local, 0))
        listener.listen(1)
        listener.settimeout(20)
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
                connection.settimeout(10)
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if sum(map(len, chunks)) > 500000:
                        raise RuntimeError('Unexpectedly large output.')
            output = b''.join(chunks).decode(errors='replace')
            try:
                stdout, stderr = proc.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                proc.terminate()
                stdout, stderr = proc.communicate(timeout=3)
            (LOCAL / (label + '-output.txt')).write_text(output)
            (LOCAL / (label + '-transport.json')).write_text(json.dumps({'returncode': proc.returncode, 'stdout': stdout, 'stderr': stderr, 'remote_probe': remote, 'time': time.time()}, indent=2))
            if BEGIN_MARK not in output or END_MARK not in output:
                raise RuntimeError('Probe incomplete; device state is unknown. Inspect current values before retrying.')
            return output
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.communicate(timeout=3)
