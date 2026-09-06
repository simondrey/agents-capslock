#!/bin/bash
set -euo pipefail
# Compatibility entry point. Prefer python3 install.py as the desktop user.
binary=${1:?built keyd binary required}
plugin=${2:?plugin directory required}
login_name=${3:-${SUDO_USER:-}}
if [[ -z $login_name || $login_name == root ]]; then
  echo 'Pass the desktop login as the third argument.' >&2
  exit 1
fi
exec python3 "$plugin/system/install-system.py" --binary "$binary" --plugin "$plugin" --user "$login_name"
