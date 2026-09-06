"""Opt-in test: isolated tmux server and its own foot window."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from attention_lib.core import Queue, run, proc
q=Queue(); tmp=tempfile.TemporaryDirectory(prefix='attention-tmux-')
base=['tmux','-S',tmp.name+'/tmux.sock','-f','/dev/null']
terminal=None
try:
    run(base+['new-session','-d','-s','attention-test','sleep 120'])
    pane=run(base+['split-window','-h','-d','-P','-F','#{pane_id}','-t','attention-test','sleep 120'])
    terminal=subprocess.Popen(['foot','--app-id=attention-tmux-test']+base+['attach-session','-t','attention-test'])
    for _ in range(40):
        win=next((w for w in json.loads(run(['hyprctl','-j','clients'])) if w['class']=='attention-tmux-test'),None)
        if win:break
        time.sleep(.1)
    assert win
    e=q.push('Select the second tmux pane',terminal.pid,{'kind':'tmux','pane':pane,'socket':tmp.name+'/tmux.sock'},'attention-tmux-test')
    q.activate(e['id'],e['revision'])
    assert run(base+['display-message','-p','-t',pane,'#{pane_active}'])=='1'
    assert json.loads(run(['hyprctl','-j','activewindow']))['address']==win['address']
    assert not any(e['id']=='attention-tmux-test' for e in q.list())
    print('PASS: exact tmux pane, visible client window, call acknowledged')
finally:
    q.remove('attention-tmux-test')
    subprocess.run(base+['kill-server'],capture_output=True)
    if terminal and terminal.poll() is None: terminal.terminate(); terminal.wait(timeout=5)
    tmp.cleanup()
