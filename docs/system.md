# System integration and rollback

The queue and UI run as the desktop user. Only the LED helper runs as root. It accepts exactly `on` or `off`, imports Python in isolated mode (`-I`), and sends an LED-only request to keyd. The sudoers rule must name the **root-owned installed helper**, never a writable copy in a home directory.

## Why a keyd extension

On the tested laptop, writes to the physical CapsLock LED sysfs node were ineffective while keyd held the keyboard. Stopping keyd allowed the write, but restarting it for every blink would disrupt typing. The supplied small patch adds three internal bind-protocol requests (`attention-led:on`, `off`, `auto`) and keeps compositor/layer LED updates from overwriting an active override. Normal keyboard mapping is unchanged by the LED extension. The public helper exposes on/off only.

The patch applies to upstream keyd v2.6.0, commit `7c0aecb8bfd34dc8642bf4eefd2e59c89e61cec3`. Upstream source/license: https://github.com/rvaiya/keyd/tree/v2.6.0 (MIT). Source is downloaded by the build script; no binary is committed to this repository.

## Default installation

Run `python3 install.py` as your desktop user. The installer builds the pinned backend without root, then uses sudo in an interactive terminal (pkexec for a noninteractive caller) for the system step. It installs the global CapsLock tap/hold mapping, LED backend and a narrow passwordless rule for that desktop user. The widget and queue remain user services.

The system step stages and checks the generated keyd configuration and sudoers fragment before replacing files. It backs up the previous versions, writes root-owned files, enables/restarts keyd and checks the LED endpoint. A failure during application attempts to restore the saved files and the previous keyd enabled/running state. Administrative authentication is needed during setup; daily use needs no password.

The preset uses `capslock = overload(agents_capslock, f24)` and a dedicated layer with J/K/L/semicolon mapped to Up/Down/Left/Right. Existing unrelated mappings, comments and device IDs are preserved. Empty/new configurations receive `[ids] *`. Multiple keyd device configuration files cause the automatic setup to stop for review. Existing device restrictions remain restrictions; extend them explicitly if you want additional keyboards covered.

The old CapsLock action is replaced. The global `overload_tap_timeout` becomes 250 ms. F24 is reserved for opening the call list. Super/Shift/Ctrl modifiers combine normally with the generated arrows; see the README shortcut table.

For separate build/system steps:

```bash
./system/build-keyd.sh
sudo python3 system/install-system.py \
  --binary "$PWD/.build/keyd/bin/keyd" --plugin "$PWD" --user "$USER"
python3 install.py --user-only
```

Installed system files:

- `/etc/keyd/default.conf`: merged keyboard configuration.
- `/usr/local/libexec/keyd-attention`: local patched backend; distribution `/usr/bin/keyd` is retained.
- `/usr/local/libexec/caps-led`: root-owned, isolated Python LED helper.
- `/etc/systemd/system/keyd.service.d/attention.conf`: local backend selection.
- `/etc/sudoers.d/agents-capslock`: only the helper's exact `on` and `off` commands; no general keyd/root access.

`~/.local/bin/caps-led` calls that helper through `sudo -n`. Existing legacy `/etc/sudoers.d/caps-led` rules are left intact. The new rule preserves grants for other users when installing again on a shared machine.

**Maintenance:** package updates do not rebuild this local keyd binary. Before upgrading the backend, port/review the patch and run the keyboard tests. The patched backend is part of the default installation, and is still an independent extension, not an upstream keyd feature. `--user-only` skips the system setup.

## Restore the previous keyboard setup

Every successful system installation prints its exact backup directory under `/var/lib/agents-capslock/backups/`. Stop the attention daemon first, then restore that backup:

```bash
systemctl --user stop omarchy-attention
sudo python3 system/install-system.py --restore /var/lib/agents-capslock/backups/PRINTED_TIMESTAMP
```

This restores the saved system files and keyd's prior service state, removing only listed files that did not exist before installation. Choose the first installation's backup to return to the pre-plugin configuration; the latest backup returns to the immediately preceding version. User widget/bindings are managed separately below. On a shared machine, restoring an old system backup also restores that backup's LED permission grants.

## Stop the plugin

```bash
systemctl --user disable --now omarchy-attention
omarchy plugin disable simondrey.agents-capslock
```

Stopping the service turns the LED off. Remove the marked two-line `omarchy-attention` block from `~/.config/hypr/bindings.lua` to release F24, then run `hyprctl reload` and `hyprctl configerrors`.

## Legacy 0.1 backup on the original development machine

First stop the user service as above. Restore the saved files and remove only the Attention service override:

```bash
sudo cp /var/lib/omarchy-attention/backup/default.conf /etc/keyd/default.conf
sudo cp /var/lib/omarchy-attention/backup/caps-led /usr/local/libexec/caps-led
sudo rm /etc/systemd/system/keyd.service.d/attention.conf
sudo systemctl daemon-reload
sudo systemctl restart keyd
```

This restores held CapsLock arrows and the previous manual `caps-led` helper (which briefly restarts keyd). The existing two-command sudoers rule remains valid. The unused local binary can remain on disk or be removed later. Do not delete unrelated keyd overrides.

## Recovery

`journalctl -u keyd` shows keyboard backend errors. `journalctl --user -u omarchy-attention` shows queue/LED failures. Upstream keyd's emergency chord is Backspace + Escape + Enter. A failure to focus a target never deletes its call; the UI displays the routing error so it can be addressed or explicitly dismissed with `attention done ID`.
