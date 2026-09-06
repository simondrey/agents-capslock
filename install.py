#!/usr/bin/env python3
"""Install Agents CapsLock, including global CapsLock navigation and LED support."""
import argparse
import getpass
import sys
import os
import json
from pathlib import Path
import shutil
import subprocess
import time
source = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--user-only', action='store_true', help='Install only the bar/queue; do not configure system keyboard or LED support')
args = parser.parse_args()
if os.geteuid() == 0:
    parser.error('Run as your desktop user; only the system step requests elevation')
if not args.user_only:
    print('CapsLock will open the call list on tap; held J/K/L/; become Up/Down/Left/Right.', flush=True)
    print('This replaces the previous CapsLock action. Other modifiers keep their normal arrow behavior.', flush=True)
    print('The system step backs up keyd settings and installs the LED backend and two narrow sudo rules.', flush=True)
    sys.path.insert(0, str(source / 'system'))
    from keyboard_config import configure
    config = Path('/etc/keyd/default.conf')
    configure(config.read_text() if config.exists() else '')  # fail before build/elevation on ambiguous config
    subprocess.run([str(source / 'system/build-keyd.sh')], check=True)
    elevation = 'sudo' if sys.stdin.isatty() else 'pkexec'
    subprocess.run([elevation, 'python3', str(source / 'system/install-system.py'),
                    '--binary', str(source / '.build/keyd/bin/keyd'), '--plugin', str(source),
                    '--user', getpass.getuser()], check=True)
home = Path.home()
target = home / '.config/omarchy/plugins/simondrey.agents-capslock'
if source != target:
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', '__pycache__', '.build'))
# Migrate the old bar ID in place, keeping the user's chosen position.
shell_config = home / '.config/omarchy/shell.json'
if shell_config.exists():
    original = shell_config.read_text()
    updated = original.replace('"simondrey.attention"', '"simondrey.agents-capslock"')
    json.loads(updated)
    if updated != original:
        shutil.copy2(shell_config, str(shell_config) + '.backup-agents-capslock-' + str(time.time_ns()))
        shell_config.write_text(updated)
old = home / '.config/omarchy/plugins/simondrey.attention'
if old.exists():
    backup = home / '.local/state/agents-capslock/backups' / ('plugin-' + str(time.time_ns()))
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old), str(backup))
binpath = home / '.local/bin/attention'
binpath.parent.mkdir(parents=True, exist_ok=True)
if binpath.exists() or binpath.is_symlink():
    if binpath.exists() and (not binpath.is_symlink() or binpath.resolve() != target / 'bin/attention'):
        shutil.copy2(binpath, str(binpath) + '.backup-' + str(time.time_ns()))
    binpath.unlink()
binpath.symlink_to(target / 'bin/attention')
alias = home / '.local/bin/agents-capslock'
if alias.exists() or alias.is_symlink():
    if not alias.is_symlink():
        shutil.copy2(alias, str(alias) + '.backup-' + str(time.time_ns()))
    alias.unlink()
alias.symlink_to(target / 'bin/attention')
led_cli = home / '.local/bin/caps-led'
if led_cli.exists() or led_cli.is_symlink():
    if not led_cli.is_symlink():
        shutil.copy2(led_cli, str(led_cli) + '.backup-' + str(time.time_ns()))
    led_cli.unlink()
led_cli.symlink_to(target / 'bin/caps-led')
units = home / '.config/systemd/user'
units.mkdir(parents=True, exist_ok=True)
(units / 'omarchy-attention.service').write_text(f'''[Unit]
Description=Agents CapsLock queue and LED indicator
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
    bindings.write_text(text + '\n' + marker + '\no.bind("F24", "Agents CapsLock", "' + str(binpath) + ' toggle")\n')
elif '"Attention calls"' in text:
    shutil.copy2(bindings, str(bindings) + '.backup-agents-capslock-' + str(time.time_ns()))
    bindings.write_text(text.replace('"Attention calls"', '"Agents CapsLock"'))
for command in (["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", "omarchy-attention"],
                ["systemctl", "--user", "restart", "omarchy-attention"],
                ["omarchy", "plugin", "enable", "simondrey.agents-capslock"],
                ["hyprctl", "reload"], ["hyprctl", "configerrors"]):
    subprocess.run(command, check=True)
print('Installed Agents CapsLock. Run: attention doctor')
