# Verification — 2026-09-06

Environment: this user's Omarchy Quickshell shell, Hyprland Lua configuration, keyd 2.6.0 plus the bundled LED patch, foot, tmux, Linux on a Dell laptop.

- Original 0.1 checks — 18 unit tests passed: concurrent queue writers, dead/zombie owner cleanup, PID reuse, lease/heartbeat, successful and failed focus, stale UI selection, replacement during focus, closest terminal ancestor, target validation, Codex/Grok/Cursor hook lifecycle parsing, delayed old-turn cleanup, and Herdr socket protocol/error handling.
- `omarchy plugin validate .` passed.
- `hyprctl reload` succeeded and `hyprctl configerrors` returned no errors.
- Real virtual-input test passed: short CapsLock produces F24; held J/K/L/semicolon produce Up/Down/Left/Right; long CapsLock hold alone does not produce F24.
- Physical LED on/off readbacks matched, and keyd's PID remained unchanged across toggles.
- Native empty and populated panels rendered and were visually inspected at the current desktop scale.
- Real desktop test passed: temporary foot window, call snapshot/bar display, observed 0/1 LED blinking, selection through the QML panel and return to the requesting window, removal after successful routing, cleanup after author exit, and LED off when empty.
- Isolated tmux server test passed: selection reached the intended second pane, focused its visible terminal client and acknowledged the call. No existing tmux sessions were modified.

Not live-tested: authenticated agent hook execution, Codex shared-daemon environment propagation, Herdr pane focus in a running session, arbitrary third-party application focus adapters, multi-monitor IPC routing and other keyboard hardware. Hook adapters are opt-in; they are not silently installed into agent configuration by the plugin installer.

## Agents CapsLock 0.2.0

- 26 unit tests pass, including MCP stdio protocol across server restarts, fresh process ownership and exit cleanup, question isolation, preservation across Stop/PostToolUse, ancestor discovery, and idempotent configuration with existing hooks/instructions preserved.
- Installed MCP tested directly on the host twice: discovered the actual running Codex PID and its foot window, created and cleared a temporary question, and worked after restarting the server. No fixed PID/window configuration was used.
- Codex CLI successfully parses and reports the installed `agents_capslock` MCP registration. Hooks are enabled in this CLI; exact new hook definitions still require the user's `/hooks` trust review.
- Real desktop and isolated tmux tests rerun successfully after plugin-ID migration: QML selection, focus, blinking LED, acknowledgement and dead-owner cleanup.
- New bar ID retained the old bar position; old installed plugin archived outside the plugin directory. Both CLI names resolve to the new installation; service remains active and the queue is empty after testing.

Not claimed: a model-driven conversation after restarting Codex, or execution of untrusted native approval hooks. The current conversation cannot load newly registered MCP tools without restarting; the host stdio protocol test verifies the server independently.

## Agents CapsLock 0.3.0 — keyboard included in installation

- 31 unit tests pass. Added fresh/existing keyd configuration merging, preservation of unrelated mappings and device selection, rejection of ambiguous mappings, idempotence, and rollback of system files after a simulated keyd startup failure.
- Built the pinned patched keyd from the upstream commit. Its native `check` accepted both a fresh generated preset and the migrated configuration from this machine.
- Ran the default `python3 install.py` successfully, including the privileged system step, sudoers validation, system backup, keyd restart and user plugin installation.
- Root virtual-keyboard test passed after installation: CapsLock tap emits F24, held J/K/L/semicolon emit Up/Down/Left/Right, long hold does not tap, and Super remains down around the generated arrows.
- Real desktop test passed again: panel selection, requesting-window focus, LED blink, dead-owner cleanup and LED off when empty. User daemon and keyd were active; no test calls remained.

A fresh machine's generated configuration was checked with keyd, not installed on a second physical computer. Stock Super-arrow focus and Super-Shift-arrow swap behavior was checked in this installed Omarchy's tiling bindings. The input test verifies actual modifier/arrow output; it does not assert every possible application or layout's response.
