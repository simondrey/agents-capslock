# Attention for Omarchy

A native Omarchy bar plugin for tools that need a human response. Calls are shown newest first. Selecting a call returns to its window or pane and acknowledges it only after successful routing. Calls disappear when their owner exits. CapsLock blinks while calls remain.

**Private preview, 0.1.0.** This is an independent plugin by simondrey, not an official Omarchy component. No public publication or upstream submission has been made.

## On this machine

The plugin, user service, CapsLock mapping and LED backend are installed.

- Click the bell in the top bar, tap CapsLock, or run `attention toggle`.
- Use arrows and Enter, or click a call, to return to the requesting tool.
- Hold CapsLock: **J = up, K = down, L = left, semicolon = right**.
- A tap is shorter than 250 ms, with no other key used. Longer holds do not open the panel.
- `caps-led on` and `caps-led off` still work without entering a password. Active attention calls temporarily control the LED.
- `attention doctor` reports the queue and service state.

## Any shell command

```bash
# Run from the terminal that will display the question.
call_id=$(attention push 'Deploy to staging?' --source deploy --pid "$$")
trap 'attention done "$call_id"' EXIT
read -r -p 'Deploy to staging? [y/N] ' answer
attention done "$call_id"
trap - EXIT
```

`--pid` is the **author**, not the short-lived `attention` command. Without it, Attention uses the `attention run` owner or its parent process. A PID is matched with its Linux process start time and boot ID, so PID reuse cannot resurrect a call. Cleanup runs every 500 ms. Exited zombies are treated as dead.

Use a stable `--id deploy:staging` to update one call instead of appending duplicates. `attention list --json` provides structured records; `attention done ID` removes a completed/cancelled request. Selecting a call only changes focus: it never approves the request or sends an answer.

For a thread or task inside a longer-running process, its integration **must send `attention done ID` when it ends**, or maintain a lease:

```bash
attention push 'Review this result' --id job:42 --pid "$$" --ttl 30
attention heartbeat job:42 --ttl 30  # renew while the task is alive
attention done job:42
```

There is no universal OS signal for a logical task ending inside a still-running process. Leases bound stale entries when its completion notification is lost. Do not use the shared server PID as the sole owner of a short-lived task.

## Exact return targets

`attention run -- TOOL ...` captures the originating window and exports `ATTENTION_TARGET` and `ATTENTION_OWNER_PID`, then execs the tool, preserving its PID, terminal and signals. Use it to make context available to hooks:

```bash
attention run -- codex
attention run -- grok
attention run -- cursor-agent
```

Inside tmux, the socket and pane ID are captured automatically. Selection switches the visible client to the right session, window and pane, unzooms if necessary, then focuses the terminal. Detached servers without a visible attached client leave the call on the list with an error.

Inside Herdr, the pane ID and session socket are captured. The native `pane.focus` API selects the pane. Start the outer Herdr session with `attention run -- herdr` so its persistent server can inherit the terminal return context; use the wrapper for the inner agent too. For an already-running server, supply an explicit `--window ADDRESS` together with a complete Herdr `--target` if context is unavailable. Herdr routing has protocol tests but has not yet been tested in a live Herdr session.

Explicit targets are accepted through `--target JSON`:

```json
{"kind":"tmux","socket":"/tmp/tmux-1000/default","pane":"%3"}
```

```json
{"kind":"herdr","socket":"/home/USER/.config/herdr/herdr.sock","pane":"w1:p2","address":"0x1234"}
```

Custom applications can provide `{"kind":"command","argv":["my-tool","focus","session-42"]}`. This is a user-level argv command, never a root command or an implicit shell expression. The adapter must return nonzero if it cannot make the requested place visible. This also allows native terminal-tab or application-thread integrations beyond window focus.

## Agent integrations

Optional installation preserves existing hook definitions and creates backups:

```bash
python3 integrations/install-hooks.py codex grok
# Cursor lifecycle cleanup, if wanted:
python3 integrations/install-hooks.py cursor
```

Restart the CLI after installing hooks and launch it through `attention run`. Codex requires review/trust of new hooks; the installer does not bypass that flow. Hook failures never approve or deny a request. The plugin's basic shell and tmux functionality needs no agent hooks.

| Tool | Adapter in this preview | Limits |
|---|---|---|
| Codex CLI | `PermissionRequest` creates a call; tool completion, next prompt, stop/interrupt/session end clear it | Arbitrary conversational questions have no automatic adapter here; shared app-server hooks must inherit or explicitly receive the originating context |
| Official Grok CLI (`@xai-official/grok`) | `Notification` permission/elicitation events create calls; lifecycle events clear them; camelCase fields supported | No completed-task/idle spam; one active call per session; hook context must propagate |
| Cursor CLI | Lifecycle hooks clear explicitly created calls | Documented hooks do not expose every approval/question wait; automatic wait detection is **not claimed** |
| tmux | Automatic pane/socket capture and exact focus | Not a universal detector of programs waiting for input |
| Herdr | Native pane focus through its socket API | No automatic agent-state watcher in this preview; use hooks or explicit calls; live validation remains pending |

Adapter parsing/lifecycle behavior is tested with representative payloads. Live authenticated Codex/Grok/Cursor agent sessions have not been driven for integration tests. A tool that lacks a reliable waiting event can call the common CLI directly. Scraping terminal text is intentionally not the integration contract.

Source contracts: [Codex hooks](https://learn.chatgpt.com/docs/hooks), [Grok hooks](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/10-hooks.md), [Cursor hooks](https://cursor.com/docs/hooks), [Herdr API source](https://github.com/herdrdev/herdr/tree/main/src/api).

## Installation elsewhere

Requires an Omarchy release using the Quickshell plugin system and Hyprland Lua dispatch, Python 3, systemd and keyd 2.6.0 for the optional LED backend. tmux and Herdr are optional.

```bash
git clone git@github.com:simondrey/omarchy-attention.git
cd omarchy-attention
python3 install.py
```

The installer copies the plugin to `~/.config/omarchy/plugins/simondrey.attention`, installs the CLI and user service, and adds F24 to the user's Hyprland bindings. Review existing F24 bindings first if installing on another machine. Updates can be applied by rerunning the installer; the daemon is restarted to load Python changes.

The native `manifest.json` also supports `omarchy plugin add` once the repository becomes accessible. The user-service/CLI setup still needs `install.py`.

### LED and CapsLock setup

See [system integration](docs/system.md). The LED extension avoids restarting keyd for each blink. The distribution's `/usr/bin/keyd` is left intact, with an explicitly installed local build selected through a systemd drop-in. This local build is pinned and is not automatically upgraded by the package manager.

## Storage and behavior

Private per-user SQLite queue at `$XDG_RUNTIME_DIR/omarchy-attention/queue.sqlite3`; it disappears on session-runtime cleanup. SQLite transactions handle simultaneous writers. `snapshot.json` is an atomically replaced view for the bar, not a file callers should edit. `ATTENTION_STATE_DIR` selects another directory for testing; the installed bar follows the standard runtime directory.

Each record contains ID, revision, title, status, source, creation time, process identity, optional lease, return target, and optional JSON metadata. No credentials or full process environment are captured. Old UI selections and simultaneous replacements are protected by revision matching. Failed focus retains the call and displays an error. Newest calls appear first; the user's selection follows its ID when the list changes.

## Verification

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Opt-in real-desktop checks (open their own test terminals): `python3 tests/live_desktop.py`, `python3 tests/live_tmux.py`. `tests/live_keyboard.py` requires root and creates a temporary virtual keyboard to verify the real keyd mapping. It does not log real keyboard input to disk. Run these only in a local test session.

See [verification notes](docs/verification.md) for the checks actually run.
