# Verification — 2026-09-06

Environment: this user's Omarchy Quickshell shell, Hyprland Lua configuration, keyd 2.6.0 plus the bundled LED patch, foot, tmux, Linux on a Dell laptop.

- 18 unit tests passed: concurrent queue writers, dead/zombie owner cleanup, PID reuse, lease/heartbeat, successful and failed focus, stale UI selection, replacement during focus, closest terminal ancestor, target validation, Codex/Grok/Cursor hook lifecycle parsing, delayed old-turn cleanup, and Herdr socket protocol/error handling.
- `omarchy plugin validate .` passed.
- `hyprctl reload` succeeded and `hyprctl configerrors` returned no errors.
- Real virtual-input test passed: short CapsLock produces F24; held J/K/L/semicolon produce Up/Down/Left/Right; long CapsLock hold alone does not produce F24.
- Physical LED on/off readbacks matched, and keyd's PID remained unchanged across toggles.
- Native empty and populated panels rendered and were visually inspected at the current desktop scale.
- Real desktop test passed: temporary foot window, call snapshot/bar display, observed 0/1 LED blinking, selection through the QML panel and return to the requesting window, removal after successful routing, cleanup after author exit, and LED off when empty.
- Isolated tmux server test passed: selection reached the intended second pane, focused its visible terminal client and acknowledged the call. No existing tmux sessions were modified.

Not live-tested: authenticated agent hook execution, Codex shared-daemon environment propagation, Herdr pane focus in a running session, arbitrary third-party application focus adapters, multi-monitor IPC routing and other keyboard hardware. Hook adapters are opt-in; they are not silently installed into agent configuration by the plugin installer.
