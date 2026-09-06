"""Private, concurrent attention queue. No third-party Python dependencies."""
import json
import os
from pathlib import Path
import re
import sqlite3
import socket
import subprocess
import time
import uuid


def proc(pid):
    try:
        fields = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return {'pid': int(pid), 'start': fields[19],
                'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (OSError, ValueError, IndexError):
        return None


def ancestors(pid):
    seen = set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        yield pid
        try:
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break


def run(argv):
    p = subprocess.run(argv, text=True, capture_output=True, timeout=5)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or 'Command failed')
    return p.stdout.strip()


def clients():
    return json.loads(run(['hyprctl', '-j', 'clients']))


def window_for(pid, windows=None):
    windows = clients() if windows is None else windows
    by_pid = {w.get('pid'): w for w in windows}
    return next((by_pid[parent] for parent in ancestors(pid) if parent in by_pid), None)


def capture_target(pid):
    target = validate_target(json.loads(os.environ['ATTENTION_TARGET'])) if os.environ.get('ATTENTION_TARGET') else {}
    try:
        win = window_for(pid)
        if win and not target:
            target = {'kind': 'window', 'address': win['address'], 'window_owner': proc(win['pid'])}
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        pass
    if os.environ.get('HERDR_ENV') == '1' and os.environ.get('HERDR_PANE_ID'):
        target.update(kind='herdr', pane=os.environ['HERDR_PANE_ID'])
        # Capture only routing context, never the caller's full environment.
        target['socket'] = herdr_socket()
    elif os.environ.get('TMUX_PANE') and os.environ.get('TMUX'):
        target.update(kind='tmux', pane=os.environ['TMUX_PANE'], socket=os.environ['TMUX'].split(',')[0])
    if not target:
        raise RuntimeError('Cannot locate the caller. Use --window ADDRESS, --target JSON, or attention run from a terminal.')
    return validate_target(target)


def herdr_socket():
    if os.environ.get('HERDR_SOCKET_PATH'):
        return os.environ['HERDR_SOCKET_PATH']
    base = Path(os.environ.get('HERDR_CONFIG_PATH', str(Path.home() / '.config/herdr/config.toml'))).parent
    if os.environ.get('HERDR_SESSION'):
        base = base / 'sessions' / os.environ['HERDR_SESSION']
    return str(base / 'herdr.sock')


def herdr_request(path, method, params):
    request_id = str(uuid.uuid4())
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(5)
        conn.connect(path)
        conn.sendall((json.dumps({'id': request_id, 'method': method, 'params': params}) + '\n').encode())
        with conn.makefile('rb') as stream:
            response = json.loads(stream.readline(2 * 1024 * 1024))
    if response.get('id') != request_id or 'error' in response or 'result' not in response:
        raise RuntimeError('Herdr: ' + str(response.get('error', 'Invalid response')))
    return response['result']


def validate_target(t):
    if not isinstance(t, dict) or t.get('kind') not in ('window', 'tmux', 'herdr', 'command'):
        raise ValueError('Invalid target kind')
    if 'address' in t and not re.fullmatch(r'0x[0-9a-fA-F]+', t['address']):
        raise ValueError('Invalid Hyprland window address')
    if t['kind'] == 'window' and 'address' not in t:
        raise ValueError('Window target needs an address')
    if t['kind'] == 'tmux' and (not re.fullmatch(r'%\d+', t.get('pane', '')) or not t.get('socket', '').startswith('/')):
        raise ValueError('tmux target needs a pane ID and absolute socket path')
    if t['kind'] == 'herdr' and (not re.fullmatch(r'w\d+:p\d+', t.get('pane', '')) or not t.get('socket', '').startswith('/')):
        raise ValueError('Invalid Herdr pane ID')
    if t['kind'] == 'command' and (not isinstance(t.get('argv'), list) or not t['argv'] or
                                  not all(isinstance(a, str) and '\0' not in a for a in t['argv'])):
        raise ValueError('Command target needs an argv array')
    return t


def focus_window(t):
    win = next((w for w in clients() if w['address'] == t['address']), None)
    if not win:
        raise RuntimeError('The target window no longer exists')
    if t.get('window_owner') and proc(win['pid']) != t['window_owner']:
        raise RuntimeError('The original window process has ended')
    reply = run(['hyprctl', 'dispatch', 'hl.dsp.focus({ window = ' + json.dumps('address:' + t['address']) + ' })'])
    if reply != 'ok':
        raise RuntimeError(reply)
    for _ in range(10):
        if json.loads(run(['hyprctl', '-j', 'activewindow'])).get('address') == t['address']:
            return
        time.sleep(.05)
    raise RuntimeError('The compositor did not focus the target window')


def focus(t):
    validate_target(t)
    if t['kind'] == 'tmux':
        base = ['tmux', '-S', t['socket']]
        info = run(base + ['display-message', '-p', '-t', t['pane'], '#{session_id}\t#{window_id}\t#{pane_id}']).split('\t')
        if len(info) != 3 or info[2] != t['pane']:
            raise RuntimeError('The tmux pane no longer exists')
        wins = clients()
        candidates = []
        for line in run(base + ['list-clients', '-F', '#{client_name}\t#{client_pid}']).splitlines():
            name, pid = line.split('\t')
            win = window_for(int(pid), wins)
            if win:
                candidates.append((name, win))
        if not candidates:
            raise RuntimeError('No visible terminal is attached to this tmux server; attach it first')
        name, win = next((c for c in candidates if c[1]['address'] == t.get('address')), candidates[0])
        run(base + ['switch-client', '-c', name, '-t', info[0]])
        run(base + ['select-window', '-t', info[1]])
        run(base + ['select-pane', '-t', t['pane']])
        # A zoomed sibling would conceal the selected pane.
        if run(base + ['display-message', '-p', '-t', t['pane'], '#{window_zoomed_flag}']) == '1':
            run(base + ['resize-pane', '-Z', '-t', t['pane']])
        focus_window({'address': win['address'], 'window_owner': proc(win['pid'])})
    elif t['kind'] == 'herdr':
        if not t.get('address'):
            raise RuntimeError('Herdr target needs its terminal window address; capture it with attention run')
        herdr_request(t['socket'], 'pane.focus', {'pane_id': t['pane']})
        focus_window(t)
    elif t['kind'] == 'command':
        run(t['argv'])
    else:
        focus_window(t)


class Queue:
    def __init__(self, directory=None):
        base = directory or os.environ.get('ATTENTION_STATE_DIR') or str(Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'omarchy-attention')
        self.directory = Path(base)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.directory.stat().st_uid != os.getuid():
            raise RuntimeError('Queue directory belongs to another user')
        self.db = sqlite3.connect(self.directory / 'queue.sqlite3', timeout=10)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, revision TEXT, data TEXT)')
        self.db.commit()

    def push(self, title, owner, target, entry_id=None, source='shell', status='waiting', ttl=None, metadata=None):
        owner_identity = proc(owner)
        if not owner_identity:
            raise ValueError('Owner process is not alive')
        if not title or len(title) > 1000:
            raise ValueError('Title must contain 1–1000 characters')
        if ttl is not None and not 0 < ttl <= 86400:
            raise ValueError('Lease must be between 0 and 86400 seconds')
        entry_id = entry_id or str(uuid.uuid4())
        if not entry_id or len(entry_id) > 300:
            raise ValueError('Invalid entry ID')
        revision = str(uuid.uuid4())
        data = dict(id=entry_id, revision=revision, title=title, source=source, status=status,
                    owner=owner_identity, target=validate_target(target), created=time.time(),
                    expires=time.time() + ttl if ttl else None, metadata=metadata or {})
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO entries VALUES (?, ?, ?)', (entry_id, revision, json.dumps(data)))
        return data

    def list(self):
        now = time.time()
        alive, stale = [], []
        for ident, rev, raw in self.db.execute('SELECT id, revision, data FROM entries'):
            data = json.loads(raw)
            if proc(data['owner']['pid']) != data['owner'] or (data['expires'] is not None and data['expires'] <= now):
                stale.append((ident, rev))
            else:
                alive.append(data)
        with self.db:
            self.db.executemany('DELETE FROM entries WHERE id=? AND revision=?', stale)
        return sorted(alive, key=lambda e: e['created'], reverse=True)

    def remove(self, ident, revision=None):
        with self.db:
            if revision:
                return self.db.execute('DELETE FROM entries WHERE id=? AND revision=?', (ident, revision)).rowcount
            return self.db.execute('DELETE FROM entries WHERE id=?', (ident,)).rowcount

    def heartbeat(self, ident, ttl):
        if not 0 < ttl <= 86400:
            raise ValueError('Invalid lease')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT data FROM entries WHERE id=?', (ident,)).fetchone()
            if not row:
                raise ValueError('Entry does not exist')
            data = json.loads(row[0]); data['expires'] = time.time() + ttl
            self.db.execute('UPDATE entries SET data=? WHERE id=?', (json.dumps(data), ident))

    def activate(self, ident, revision=None):
        item = next((e for e in self.list() if e['id'] == ident), None)
        if not item or (revision and item['revision'] != revision):
            raise RuntimeError('This call has expired or changed; refresh the list')
        focus(item['target'])
        # A new request with the same ID while focusing must survive.
        self.remove(ident, item['revision'])
