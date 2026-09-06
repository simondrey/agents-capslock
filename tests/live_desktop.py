"""Opt-in desktop integration test: opens and closes only its own terminal."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from attention_lib.core import Queue, proc, run
q = Queue()
terminal = subprocess.Popen(['foot', '--app-id=attention-test', '--title=Attention test', 'sh', '-c', 'printf "Attention integration test — waiting here.\\n"; sleep 120'])
ident = 'attention-live-test'
try:
    win = None
    for _ in range(40):
        win = next((w for w in json.loads(run(['hyprctl', '-j', 'clients'])) if w['class'] == 'attention-test'), None)
        if win: break
        time.sleep(.1)
    assert win, 'Test terminal did not appear'
    entry = q.push('Test: this terminal needs your attention', terminal.pid,
                   {'kind': 'window', 'address': win['address'], 'window_owner': proc(win['pid'])}, ident, 'Integration test')
    time.sleep(.7)
    run(['omarchy-shell', 'simondrey.attention', 'open']); time.sleep(.6)
    subprocess.run(['grim', '/tmp/attention-populated.png'], check=True)
    readings=[]
    for _ in range(14):
        readings.append(Path('/sys/class/leds/input3::capslock/brightness').read_text().strip())
        time.sleep(.1)
    assert set(readings) == {'0','1'}, readings
    run(['omarchy-shell', 'simondrey.attention', 'activate'])
    for _ in range(40):
        if not any(e['id']==ident for e in q.list()): break
        time.sleep(.1)
    assert json.loads(run(['hyprctl', '-j', 'activewindow']))['address'] == win['address']
    assert not any(e['id']==ident for e in q.list())
    q.push('Dies with its author', terminal.pid, {'kind':'window','address':win['address']}, ident)
    terminal.terminate(); terminal.wait(timeout=5)
    time.sleep(.8)
    assert not any(e['id']==ident for e in q.list())
    assert Path('/sys/class/leds/input3::capslock/brightness').read_text().strip() == '0'
    print('PASS: populated panel, blinking LED, focus acknowledgement, dead-owner cleanup, LED off')
finally:
    q.remove(ident)
    if terminal.poll() is None:
        terminal.terminate(); terminal.wait(timeout=5)
    run(['omarchy-shell','simondrey.attention','close'])
