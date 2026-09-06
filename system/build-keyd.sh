#!/bin/bash
set -euo pipefail
plugin_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
build_dir="$plugin_dir/.build/keyd"
commit=7c0aecb8bfd34dc8642bf4eefd2e59c89e61cec3
if [[ ! -d "$build_dir" ]]; then
  git clone --branch v2.6.0 --depth 1 https://github.com/rvaiya/keyd.git "$build_dir"
  [[ $(git -C "$build_dir" rev-parse HEAD) == "$commit" ]] || { echo 'Unexpected keyd commit' >&2; exit 1; }
fi
[[ $(git -C "$build_dir" rev-parse HEAD) == "$commit" ]] || exit 1
if ! git -C "$build_dir" apply --reverse --check "$plugin_dir/system/keyd-led.patch" 2>/dev/null; then
  git -C "$build_dir" apply --check "$plugin_dir/system/keyd-led.patch"
  git -C "$build_dir" apply "$plugin_dir/system/keyd-led.patch"
fi
make -C "$build_dir" PREFIX=/usr
printf '\nBuilt %s/bin/keyd\n' "$build_dir"
