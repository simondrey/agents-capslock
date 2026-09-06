#!/bin/bash
set -euo pipefail
# Run as root after reviewing this script. Arguments: built keyd binary, plugin directory.
binary=$1
plugin=$2
backup=/var/lib/omarchy-attention/backup
install -d -m 700 "$backup"
for original in /etc/keyd/default.conf /usr/local/libexec/caps-led; do
  name=${original##*/}
  if [[ -f $original && ! -e $backup/$name ]]; then cp -a "$original" "$backup/$name"; fi
done
install -d -m 755 /usr/local/libexec /etc/systemd/system/keyd.service.d
install -o root -g root -m 755 "$binary" /usr/local/libexec/keyd-attention
install -o root -g root -m 755 "$plugin/system/caps-led" /usr/local/libexec/caps-led
install -o root -g root -m 644 "$plugin/system/attention-keyd.conf" /etc/systemd/system/keyd.service.d/attention.conf
python3 - <<'PY'
from pathlib import Path
p = Path('/etc/keyd/default.conf')
s = p.read_text()
old = 'capslock = layer(arrows)'
new = 'capslock = overload(arrows, f24)'
if old not in s and new not in s:
    raise SystemExit('Unrecognized CapsLock mapping; edit configuration manually')
s = s.replace(old, new)
if '[global]' not in s:
    s += '\n[global]\noverload_tap_timeout = 250\n'
elif 'overload_tap_timeout' not in s:
    s = s.replace('[global]', '[global]\noverload_tap_timeout = 250')
p.write_text(s)
PY
/usr/local/libexec/keyd-attention check /etc/keyd/default.conf
systemctl daemon-reload
systemctl restart keyd
# Type=simple starts before its socket is ready.
for attempt in {1..30}; do
  if /usr/local/libexec/caps-led off 2>/dev/null; then exit 0; fi
  sleep 0.1
done
echo 'LED backend did not start; inspect journalctl -u keyd' >&2
exit 1
