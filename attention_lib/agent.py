"""Resolve a local agent's identity on each launch, never from a saved PID."""
import os
from pathlib import Path
from .core import ancestors, capture_target, proc


def context(provider='codex'):
    explicit = os.environ.get('ATTENTION_OWNER_PID')
    if explicit:
        owner = int(explicit)
    else:
        owner = None
        for pid in ancestors(os.getpid()):
            try:
                name = Path(f'/proc/{pid}/comm').read_text().strip()
            except OSError:
                continue
            if name == provider:
                owner = pid
                break
        if owner is None:
            raise RuntimeError('No local agent ancestor. Launch through attention run -- TOOL, or forward ATTENTION_OWNER_PID and ATTENTION_TARGET to the MCP server.')
    identity = proc(owner)
    if not identity:
        raise RuntimeError('The agent process has ended')
    return identity, capture_target(owner)


def question_id(session):
    if not isinstance(session, str) or not session or len(session) > 220:
        raise ValueError('conversation_id must contain 1–220 characters')
    return 'codex:' + session + ':question'


def request(q, session, message):
    identity, target = context()
    item = q.push(message, identity['pid'], target, question_id(session), 'Codex', 'waiting for your answer',
                  metadata={'session_id': session, 'channel': 'question'})
    return {'id': item['id'], 'revision': item['revision'], 'owner': identity, 'target': target}


def clear(q, session):
    return {'removed': bool(q.remove(question_id(session)))}
