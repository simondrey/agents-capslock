# System integration and rollback

The queue and UI run as the desktop user. Only the LED helper runs as root. It accepts exactly `on` or `off`, imports Python in isolated mode (`-I`), and sends an LED-only request to keyd. The sudoers rule must name the **root-owned installed helper**, never a writable copy in a home directory.

## Why a keyd extension

On the tested laptop, writes to the physical CapsLock LED sysfs node were ineffective while keyd held the keyboard. Stopping keyd allowed the write, but restarting it for every blink would disrupt typing. The supplied small patch adds three internal bind-protocol requests (`attention-led:on`, `off`, `auto`) and keeps compositor/layer LED updates from overwriting an active override. Normal keyboard mapping is unchanged by the LED extension. The public helper exposes on/off only.

The patch applies to upstream keyd v2.6.0, commit `7c0aecb8bfd34dc8642bf4eefd2e59c89e61cec3`. Upstream source/license: https://github.com/rvaiya/keyd/tree/v2.6.0 (MIT). Source is downloaded by the build script; no binary is committed to this repository.

## Build and install

```bash
./system/build-keyd.sh
# Review system/install-local-led.sh before running it.
sudo ./system/install-local-led.sh "$PWD/.build/keyd/bin/keyd" "$PWD"
```

This installer is tailored to the existing CapsLock arrows preset: `/etc/keyd/default.conf` must contain `capslock = layer(arrows)` or the installed `capslock = overload(arrows, f24)`. Review/adapt other keyd configurations before using it. It sets a 250 ms maximum tap duration and leaves the arrows layer intact. F24 is reserved for the user's Hyprland Attention binding.

On a new machine, create the narrow sudoers rule with `sudo visudo -f /etc/sudoers.d/caps-led`, substituting your login name:

```sudoers
YOUR_LOGIN ALL=(root) NOPASSWD: /usr/local/libexec/caps-led on, /usr/local/libexec/caps-led off
```

The installer selects `/usr/local/libexec/keyd-attention` through `/etc/systemd/system/keyd.service.d/attention.conf`. `/usr/bin/keyd` is not replaced. The first original configuration and old helper are saved under `/var/lib/omarchy-attention/backup/`.

**Maintenance:** package updates do not rebuild this local keyd binary. Before upgrading the backend, port/review the patch and run the keyboard tests. The patch is an optional compatibility dependency of this private preview, not an upstream keyd feature.

## Stop the plugin

```bash
systemctl --user disable --now omarchy-attention
omarchy plugin disable simondrey.attention
```

Stopping the service turns the LED off. Remove the marked two-line `omarchy-attention` block from `~/.config/hypr/bindings.lua` to release F24, then run `hyprctl reload` and `hyprctl configerrors`.

## Restore this machine's previous CapsLock/LED setup

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
