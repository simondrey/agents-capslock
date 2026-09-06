"""Small local MCP stdio server: attention signaling only, no command execution."""
import json
import sys
from .core import Queue
from .agent import context, request, clear

TOOLS = [
    {'name': 'request_attention', 'description': 'Signal that this Codex conversation needs a human answer. Call immediately before asking the user; not for task completion or routine progress. Returns to this agent terminal when selected.',
     'inputSchema': {'type': 'object', 'properties': {'conversation_id': {'type': 'string', 'description': 'The current CODEX_THREAD_ID; keep stable within this conversation'}, 'message': {'type': 'string', 'description': 'A concise version of the question, in the user language'}}, 'required': ['conversation_id', 'message'], 'additionalProperties': False},
     'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}},
    {'name': 'clear_attention', 'description': 'Remove this conversation question when the human replies, the question is withdrawn, or it is no longer needed. Safe when already removed by clicking or hooks.',
     'inputSchema': {'type': 'object', 'properties': {'conversation_id': {'type': 'string'}}, 'required': ['conversation_id'], 'additionalProperties': False},
     'annotations': {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}},
    {'name': 'connection_status', 'description': 'Check current agent process and return target without adding a call.',
     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False},
     'annotations': {'readOnlyHint': True, 'openWorldHint': False}}
]


def dispatch(method, params):
    if method == 'initialize':
        return {'protocolVersion': params.get('protocolVersion', '2024-11-05'), 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'agents-capslock', 'version': '0.2.0'},
                'instructions': 'Use request_attention before a real question, clear_attention on reply. Do not signal ordinary completion. Use the current CODEX_THREAD_ID as conversation_id.'}
    if method == 'ping': return {}
    if method == 'tools/list': return {'tools': TOOLS}
    if method in ('resources/list', 'resources/templates/list', 'prompts/list'):
        return { {'resources/list':'resources','resources/templates/list':'resourceTemplates','prompts/list':'prompts'}[method]: [] }
    if method != 'tools/call': raise LookupError('Method not found')
    name = params.get('name')
    args = params.get('arguments', {})
    try:
        schema = next((t['inputSchema'] for t in TOOLS if t['name'] == name), None)
        if schema is None: raise ValueError('Unknown tool')
        if not isinstance(args, dict) or set(args) - set(schema['properties']): raise ValueError('Unexpected arguments')
        for key in schema.get('required', []):
            if not isinstance(args.get(key), str): raise ValueError('Missing string argument: ' + key)
        if name == 'connection_status':
            owner, target = context(); result = {'connected': True, 'owner': owner, 'target': target}
        else:
            q = Queue()
            try:
                result = request(q, args['conversation_id'], args['message']) if name == 'request_attention' else clear(q, args['conversation_id'])
            finally: q.db.close()
        return {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}], 'isError': False}
    except (OSError, ValueError, RuntimeError) as e:
        return {'content': [{'type': 'text', 'text': str(e)}], 'isError': True}


def serve():
    for line in sys.stdin.buffer:
        ident = None
        try:
            if len(line) > 1024 * 1024: raise ValueError('Message too large')
            message = json.loads(line)
            if not isinstance(message, dict): raise ValueError('Expected an object')
            ident = message.get('id')
            if 'id' not in message: continue  # notifications have no response
            params = message.get('params', {})
            if not isinstance(params, dict): raise ValueError('Expected object params')
            result = dispatch(message.get('method'), params)
            response = {'jsonrpc': '2.0', 'id': ident, 'result': result}
        except LookupError as e:
            response = {'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32601, 'message': str(e)}}
        except (ValueError, TypeError) as e:
            response = {'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32600, 'message': str(e)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)
