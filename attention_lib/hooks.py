"""Passive adapters. They never approve, reject, or resume an agent."""
import os
from .core import capture_target
from .agent import context, question_id

CLEAR = {'SessionEnd', 'SessionStart', 'UserPromptSubmit', 'PostToolUse', 'PostToolUseFailure',
         'Interrupt', 'Stop', 'StopFailure', 'StopCancelled', 'sessionStart', 'sessionEnd',
         'beforeSubmitPrompt', 'postToolUse', 'afterShellExecution', 'stop'}


def handle(q, provider, data):
    session = str(data.get('session_id') or data.get('sessionId') or data.get('conversation_id') or
                  os.environ.get('GROK_SESSION_ID') or os.environ.get('ATTENTION_SESSION', ''))
    if not session:
        raise ValueError('Hook has no session ID')
    ident = provider + ':' + session
    event = data.get('hook_event_name') or data.get('event')
    if not event:
        event = ''.join(w.title() for w in str(data.get('hookEventName') or os.environ.get('GROK_HOOK_EVENT', '')).split('_'))
    turn = data.get('turn_id') or data.get('promptId')
    if event in CLEAR:
        # A question intentionally survives Stop: ending a turn can mean waiting for a reply.
        if provider == 'codex' and event in ('SessionStart', 'SessionEnd', 'UserPromptSubmit'):
            q.remove(question_id(session))
        existing = next((e for e in q.list() if e['id'] == ident), None)
        if existing:
            # Delayed completion for an older turn must not erase a newer call.
            previous_turn = existing['metadata'].get('turn_id')
            if event in ('SessionEnd', 'SessionStart', 'UserPromptSubmit', 'sessionStart', 'sessionEnd', 'beforeSubmitPrompt') or not turn or not previous_turn or turn == previous_turn:
                q.remove(ident, existing['revision'])
    elif event in ('PermissionRequest', 'Notification', 'notification'):
        notification = data.get('notification_type') or data.get('notificationType')
        # Completed work is deliberately not an attention call.
        if event != 'PermissionRequest' and notification not in ('permission_prompt', 'elicitation_dialog'):
            return
        owner = int(os.environ.get('ATTENTION_OWNER_PID', '0'))
        if not owner:
            identity, target = context(provider)
            owner = identity['pid']
        else:
            target = capture_target(owner)
        tool_input = data.get('tool_input') or data.get('toolInput') or {}
        description = tool_input.get('description') if isinstance(tool_input, dict) else None
        title = data.get('message') or description or 'Approval or answer required'
        q.push(str(title)[:1000], owner, target, ident, provider, 'waiting',
               metadata={'session_id': session, 'turn_id': turn, 'event': event})
