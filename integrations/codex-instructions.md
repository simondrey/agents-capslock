<!-- agents-capslock:begin -->
## Agents CapsLock — requests for the user's attention

The user has connected this Codex CLI to the local Agents CapsLock plugin.

- At the start of a conversation, obtain the current `CODEX_THREAD_ID` from the shell environment once; use that exact value as `conversation_id`. Do not reuse IDs from earlier conversations or hardcode a PID/window address.
- Before asking the user a question that needs an answer, call the `agents_capslock` MCP tool `request_attention` with that conversation ID and a short version of the question in the user's language. This includes clarification questions, choices and requests for user input. Then ask the question using the normal conversation/input tool. If there are several simultaneous questions, summarize them in one call.
- When the user replies, call `clear_attention` for this conversation before resuming work. Also clear it if you withdraw the question or no longer need the answer. Both operations are idempotent. Clear only your own conversation.
- Do not request attention for progress updates, successful task completion, or a final answer that does not ask the user to respond. Do not clear a real unanswered question just because your turn ends. Selecting a call only focuses the conversation; it is not an answer or approval.
- Use the MCP tools directly; they run locally outside the command sandbox and need no sudo. Discover the `agents_capslock` tools if they are deferred. Do not replace them with repeated privileged shell commands.
- If MCP is unavailable or reports a routing error, ask the user normally and state briefly that the indicator could not be updated. Do not invent success, block the task, or keep retrying indefinitely. `agents-capslock agent-status` can diagnose the connection from the host terminal.

This is a notification/focus integration only. It never authorizes a command, answers a prompt, or changes an agent's approval policy. Native Codex approval dialogs are additionally observed by the optional trusted lifecycle hooks.
<!-- agents-capslock:end -->
