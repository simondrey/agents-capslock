# Connecting your agent to Agents CapsLock

Connecting means teaching a tool **when it needs a human**, **which live task owns the call**, **where the human can respond**, and **when that call is no longer relevant**. The plugin displays calls, blinks CapsLock, routes selection and cleans up dead owners. It does not infer arbitrary agent state from terminal text or answer a prompt on your behalf.

## Codex CLI: persistent setup

Install Agents CapsLock first, then run:

```bash
python3 integrations/connect-codex.py
```

The connector preserves existing settings and creates timestamped backups. It writes these managed additions to `${CODEX_HOME:-$HOME/.codex}`:

1. `config.toml`: a local stdio MCP server named `agents_capslock`, with only three allowed tools. These notification tools are preapproved so signaling attention does not itself require approval. Shell-command permissions are unchanged.
2. `AGENTS.md` (or an existing nonempty `AGENTS.override.md`): an instruction to signal immediately before asking a real question and clear after the response. Other instructions are preserved.
3. `hooks.json`: passive handlers for native permission requests and lifecycle cleanup. Other hook handlers are preserved.

Restart Codex to load the server and instruction chain. Review and trust the new hook definitions using `/hooks`; the connector deliberately does not modify Codex's hook trust records. The MCP question tools work independently of trusted hooks. Hook failures neither approve nor reject actions.

For a nondefault installation:

```bash
python3 integrations/connect-codex.py \
  --codex-home /home/USER/.codex \
  --plugin-dir /home/USER/.config/omarchy/plugins/simondrey.agents-capslock
```

No PID, thread ID or window address is saved in configuration. On each launch, the local server finds the nearest Codex ancestor and resolves its terminal. It inherits only listed routing environment variables, including tmux/Herdr context. Restarting the agent therefore gets a fresh owner automatically. Entries owned by the old process disappear when it exits. Resuming a conversation does not resurrect an obsolete question; a new question creates a new call.

For remote processes, persistent shared servers or unusual launchers, propagate explicit originating context:

```bash
attention run -- codex
```

A window address alone cannot identify an application tab or a task inside a shared server. Such integrations need a native pane/session adapter, not just the server PID. See the return target examples in the README.

## What the agent does

At conversation start the agent reads its actual `CODEX_THREAD_ID`. Immediately before a question it calls the MCP tool:

```json
{
  "name": "request_attention",
  "arguments": {
    "conversation_id": "CURRENT_CODEX_THREAD_ID",
    "message": "Which deployment environment should I use?"
  }
}
```

It then asks through its normal conversation UI. On reply or withdrawal it calls `clear_attention` with the same `conversation_id`. `connection_status` reports the current process identity and return target without creating an entry. These are tool names on the `agents_capslock` server; a client may prefix their displayed names.

One stable ID (`codex:CONVERSATION:question`) updates the conversation's existing question. Different conversations remain separate. Question entries survive `Stop` and `PostToolUse`, because finishing a turn or signaling through MCP does not imply an answer. `UserPromptSubmit`, `SessionStart` and `SessionEnd` clear question entries; native approval calls use a separate ID and lifecycle. Selecting a call acknowledges the list entry and focuses the tool but does not answer it.

This mechanism depends on the agent following its instruction. A deterministic application should invoke the same queue operations directly at its actual input/approval boundary. There is no claim that an instruction intercepts every possible wait inside every CLI.

## Other agents and command-line programs

The common CLI needs no MCP support:

```bash
# Execute in the process/terminal that actually displays the question.
request_id="my-agent:${TASK_ID}:question"
attention push 'Choose the next step' --id "$request_id" --source my-agent --pid "$$"
# Display your prompt and wait for a human response here.
attention done "$request_id"
```

Use a live author PID, not the short-lived helper's PID. For an internal task that can finish while its process continues, call `done` on cancellation/completion too, or set `--ttl 30` and renew with `attention heartbeat "$request_id" --ttl 30` while that task remains alive. Provide a captured `ATTENTION_TARGET`, explicit `--target` or a supported terminal context so selection reaches the correct place.

An integration can use native CLI hooks, call the command directly from application code, or expose equivalent tools through its own MCP server. The bundled MCP server resolves Codex ownership by default; other providers should use the common CLI or explicitly forward owner and target context, and use their own source/ID namespace. The Grok and Cursor hook adapters are described in the README. Do not label task completion as a request for input.

## Check and troubleshoot

```bash
codex mcp get agents_capslock --json
agents-capslock doctor
attention list --json
```

Within Codex, call `connection_status`. For a host-terminal diagnostic, `attention run -- agents-capslock agent-status` provides explicit context even outside a Codex process. `agent-status` directly in an unrelated shell has no agent ancestor and correctly reports that missing context.

If tools are missing, restart Codex and check its MCP status. If only native approval dialogs are missing, check `/hooks` trust. If routing fails, ensure the server runs on the same desktop with the correct tmux/Herdr environment. A failed focus keeps the entry available instead of silently acknowledging it. No sudo is required for queue operations; LED privileges belong to the separate installed LED backend.

To disconnect, remove only the `agents-capslock:begin/end` managed blocks from the Codex config/instructions and the matching `attention hook codex` commands from `hooks.json`, then restart Codex. The connector's backups can help inspect earlier settings; avoid overwriting unrelated later changes.

## Naming and compatibility

The plugin name is **Agents CapsLock**, ID `simondrey.agents-capslock`, repository `simondrey/agents-capslock`. `agents-capslock` is the new command alias; `attention` remains supported. Internal `ATTENTION_*` variables, the `omarchy-attention.service` unit, runtime directory and existing privileged keyd/LED backend names remain stable for compatibility.

References: [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex hooks and trust](https://learn.chatgpt.com/docs/hooks).
