import os
import tempfile
import unittest
from unittest.mock import patch
from attention_lib.core import Queue
from attention_lib.hooks import handle

class Hooks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.q=Queue(self.tmp.name)
        self.env=patch.dict(os.environ,{'ATTENTION_OWNER_PID':str(os.getpid())})
        self.env.start()
        self.target=patch('attention_lib.hooks.capture_target',return_value={'kind':'command','argv':['true']})
        self.target.start()
    def tearDown(self):
        self.target.stop();self.env.stop();self.q.db.close();self.tmp.cleanup()
    def test_codex_approval_and_resume(self):
        handle(self.q,'codex',{'session_id':'s','hook_event_name':'PermissionRequest','turn_id':'t'})
        self.assertEqual(len(self.q.list()),1)
        handle(self.q,'codex',{'session_id':'s','hook_event_name':'PostToolUse','turn_id':'t'})
        self.assertEqual(self.q.list(),[])
    def test_grok_camel_case(self):
        handle(self.q,'grok',{'sessionId':'s','hookEventName':'notification','notificationType':'permission_prompt'})
        self.assertEqual(self.q.list()[0]['id'],'grok:s')
    def test_completion_is_not_attention(self):
        handle(self.q,'grok',{'sessionId':'s','hookEventName':'notification','notificationType':'task_complete'})
        self.assertEqual(self.q.list(),[])
    def test_old_turn_end_does_not_clear_new_call(self):
        handle(self.q,'grok',{'sessionId':'s','hook_event_name':'Notification','notificationType':'permission_prompt','promptId':'new'})
        handle(self.q,'grok',{'sessionId':'s','hook_event_name':'Stop','promptId':'old'})
        self.assertEqual(len(self.q.list()),1)
    def test_cursor_stop_clears_explicit_call(self):
        self.q.push('Question',os.getpid(),{'kind':'command','argv':['true']},'cursor:s')
        handle(self.q,'cursor',{'conversation_id':'s','hook_event_name':'stop'})
        self.assertEqual(self.q.list(),[])
