#!/usr/bin/env python3
"""Install or restore the root-owned keyboard/LED portion of Agents CapsLock."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tempfile
import time
from keyboard_config import configure

BACKUPS = Path('/var/lib/agents-capslock/backups')
CONFIG = Path('/etc/keyd/default.conf')
BINARY = Path('/usr/local/libexec/keyd-attention')
HELPER = Path('/usr/local/libexec/caps-led')
OVERRIDE = Path('/etc/systemd/system/keyd.service.d/attention.conf')
SUDOERS = Path('/etc/sudoers.d/agents-capslock')
FILES = (CONFIG, BINARY, HELPER, OVERRIDE, SUDOERS)


def run(*args):
    subprocess.run(args, check=True)


def restore(backup):
    backup = backup.resolve()
    if backup.parent != BACKUPS or not backup.is_dir():
        raise ValueError('Choose a backup directory directly under ' + str(BACKUPS))
    manifest = json.loads((backup/'manifest.json').read_text())
    for path in FILES:
        saved = backup/path.name
        if manifest['existed'][str(path)]:
            temporary = path.with_name(path.name+".agents-capslock.restore")
            temporary.unlink(missing_ok=True)
            shutil.copy2(saved, temporary)
            temporary.replace(path)
        else:
            path.unlink(missing_ok=True)
    run('systemctl', 'daemon-reload')
    if manifest['enabled'] == 'enabled':
        run('systemctl', 'enable', 'keyd')
    else:
        run('systemctl', 'disable', 'keyd')
    run('systemctl', 'restart' if manifest['active'] else 'stop', 'keyd')


def install(binary, plugin, user):
    pwd.getpwnam(user)
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_-]*\$?', user):
        raise ValueError('Unsupported login name for sudoers')
    for command in ('systemctl', 'visudo'):
        if not shutil.which(command):
            raise ValueError('Required command missing: ' + command)
    # Other device-specific files may win keyd matching and bypass default.conf.
    others = sorted(CONFIG.parent.glob('*.conf'))
    others = [str(p) for p in others if p != CONFIG]
    if others:
        raise ValueError('Additional keyd device configurations need review before automatic setup: ' + ', '.join(others))
    keyboard = configure(CONFIG.read_text() if CONFIG.exists() else '')
    rule = f'{user} ALL=(root) NOPASSWD: {HELPER} on, {HELPER} off\n'
    # Preserve grants for other users on a shared machine.
    if SUDOERS.exists():
        existing = SUDOERS.read_text()
        if rule not in existing.splitlines(keepends=True):
            rule = existing.rstrip() + '\n' + rule
        else:
            rule = existing
    with tempfile.TemporaryDirectory(prefix='agents-capslock-') as directory:
        stage = Path(directory)
        (stage/'default.conf').write_text(keyboard)
        (stage/'sudoers').write_text(rule)
        run(str(binary), 'check', str(stage/'default.conf'))
        run('visudo', '-cf', str(stage/'sudoers'))
        for required in (binary, plugin/'system/caps-led', plugin/'system/attention-keyd.conf'):
            if not required.is_file():
                raise ValueError('Missing installation file: ' + str(required))
        backup = BACKUPS/str(time.time_ns())
        backup.mkdir(parents=True, mode=0o700)
        manifest = {'existed': {str(p): p.exists() for p in FILES},
                    'enabled': subprocess.run(['systemctl','is-enabled','keyd'], capture_output=True,text=True).stdout.strip(),
                    'active': subprocess.run(['systemctl','is-active','--quiet','keyd']).returncode == 0}
        for path in FILES:
            if path.exists():
                shutil.copy2(path, backup/path.name)
        (backup/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        try:
            for src, dest, mode in ((stage/'default.conf', CONFIG, 0o644), (binary, BINARY, 0o755),
                                    (plugin/'system/caps-led', HELPER, 0o755),
                                    (plugin/'system/attention-keyd.conf', OVERRIDE, 0o644),
                                    (stage/'sudoers', SUDOERS, 0o440)):
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Replace, rather than follow, any old destination symlink.
                temporary = dest.with_name(dest.name+'.agents-capslock.tmp')
                temporary.unlink(missing_ok=True)
                shutil.copyfile(src, temporary)
                os.chmod(temporary, mode)
                temporary.replace(dest)
            run('systemctl','daemon-reload')
            run('systemctl','enable','--now','keyd')
            run('systemctl','restart','keyd')
            for _ in range(30):
                if subprocess.run([str(HELPER),'off'],capture_output=True).returncode == 0:
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('LED backend did not become ready')
        except Exception:
            restore(backup)
            raise
        print('Installed CapsLock tap/hold, LED backend and passwordless LED commands.')
        print('System backup:', backup)
        print('Restore with: sudo python3 system/install-system.py --restore ' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--plugin', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--user')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Run this system step with sudo (or pkexec without an interactive terminal)')
    try:
        if args.restore:
            restore(args.restore)
        else:
            if not args.binary or not args.user:
                parser.error('--binary and --user are required for installation')
            install(args.binary.resolve(), args.plugin.resolve(), args.user)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error)+'\n')
