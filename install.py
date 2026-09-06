#!/usr/bin/env python3
"""Install the user plugin and service. Does not install privileged LED support."""
import os
from pathlib import Path
import shutil
import subprocess
import time
source = Path(__file__).resolve().parent
home = Path.home()
target = home / '.config/omarchy/plugins/simondrey.attention'
if source != target:
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '__pycache__', '.build'))
binpath = home / '.local/bin/attention'
binpath.parent.mkdir(parents=True, exist_ok=True)
if binpath.exists() or binpath.is_symlink():
    if not binpath.is_symlink() or binpath.resolve() != target / 'bin/attention':
        shutil.copy2(binpath, str(binpath) + '.backup-' + str(time.time_ns()))
    binpath.unlink()
binpath.symlink_to(target / 'bin/attention')
units = home / '.config/systemd/user'
units.mkdir(parents=True, exist_ok=True)
(units / 'omarchy-attention.service').write_text(f'''[Unit]
Description=Omarchy attention queue and LED indicator
After=graphical-session.target
PartOf=graphical-session.target

[Service]
ExecStart="{target}/bin/attention" daemon
ExecStopPost=/usr/bin/sudo -n /usr/local/libexec/caps-led off
Restart=on-failure
RestartSec=2
UMask=0077

[Install]
WantedBy=graphical-session.target
''')
bindings = home / '.config/hypr/bindings.lua'
text = bindings.read_text()
marker = '-- omarchy-attention: tap CapsLock (keyd emits F24)'
if marker not in text:
    shutil.copy2(bindings, str(bindings) + '.backup-attention-' + str(time.time_ns()))
    bindings.write_text(text + '\n' + marker + '\no.bind("F24", "Attention calls", "' + str(binpath) + ' toggle")\n')
for command in (["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", "omarchy-attention"],
                ["systemctl", "--user", "restart", "omarchy-attention"],
                ["omarchy", "plugin", "enable", "simondrey.attention"],
                ["hyprctl", "reload"], ["hyprctl", "configerrors"]):
    subprocess.run(command, check=True)
print('Installed Attention. Run: attention doctor')
