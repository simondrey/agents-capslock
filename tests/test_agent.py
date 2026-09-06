import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from attention_lib import agent, mcp
from attention_lib.core import Queue
from attention_lib.hooks import handle

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('connect_codex', ROOT/'integrations/connect-codex.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class AgentIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.q = Queue(self.tmp.name)
        self.env = patch.dict(os.environ, {'ATTENTION_OWNER_PID':str(os.getpid()), 'ATTENTION_TARGET':json.dumps({'kind':'command','argv':['true']})})
        self.env.start()
    def tearDown(self):
        self.env.stop(); self.q.db.close(); self.tmp.cleanup()
    def test_questions_survive_turn_end_and_tool_completion(self):
        agent.request(self.q,'one','Continue?')
        agent.request(self.q,'two','Choose?')
        for event in ('Stop','PostToolUse'):
            handle(self.q,'codex',{'session_id':'one','hook_event_name':event})
            self.assertEqual(len(self.q.list()),2)
        handle(self.q,'codex',{'session_id':'one','hook_event_name':'UserPromptSubmit'})
        self.assertEqual([x['id'] for x in self.q.list()],['codex:two:question'])
        handle(self.q,'codex',{'session_id':'two','hook_event_name':'SessionEnd'})
        self.assertEqual(self.q.list(),[])
    def test_new_owner_after_restart_and_cleanup(self):
        owners=[]
        for _ in range(2):
            child=subprocess.Popen(['sleep','60'])
            try:
                with patch.dict(os.environ,{'ATTENTION_OWNER_PID':str(child.pid)}):
                    result=agent.request(self.q,'resumed','Question')
                    owners.append(result['owner']['pid'])
                    self.assertEqual(len(self.q.list()),1)
            finally:
                child.terminate();child.wait()
            self.assertEqual(self.q.list(),[])
        self.assertNotEqual(*owners)
    def test_discover_agent_ancestor(self):
        with patch.dict(os.environ,{'ATTENTION_OWNER_PID':''}), patch.object(agent,'ancestors',return_value=[44,55]), patch.object(Path,'read_text',side_effect=['python3','codex']), patch.object(agent,'proc',return_value={'pid':55}), patch.object(agent,'capture_target',return_value={'address':'0x1'}) as capture:
            self.assertEqual(agent.context()[0]['pid'],55)
            capture.assert_called_once_with(55)
    def test_unknown_context_fails_closed(self):
        with patch.dict(os.environ,{'ATTENTION_OWNER_PID':''}), patch.object(agent,'ancestors',return_value=[]):
            with self.assertRaises(RuntimeError): agent.request(self.q,'one','Question')
        self.assertEqual(self.q.list(),[])
    def test_mcp_rejects_extra_arguments(self):
        result=mcp.dispatch('tools/call',{'name':'request_attention','arguments':{'conversation_id':'s','message':'Question','command':'false'}})
        self.assertTrue(result['isError'])
    def test_stdio_restarts_and_protocol(self):
        for _ in range(2):
            messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}},
                      {'jsonrpc':'2.0','method':'notifications/initialized'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                      {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'connection_status'}}]
            result=subprocess.run([str(ROOT/'bin/agents-capslock-mcp')],input='\n'.join(map(json.dumps,messages))+'\n',capture_output=True,text=True,check=True)
            replies=list(map(json.loads,result.stdout.splitlines()))
            self.assertEqual([r['id'] for r in replies],[1,2,3])
            self.assertEqual(len(replies[1]['result']['tools']),3)
            self.assertFalse(replies[2]['result']['isError'])
            self.assertEqual(result.stderr,'')

class Configuration(unittest.TestCase):
    def test_idempotent_preserves_existing_settings_and_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            (home/'config.toml').write_text('model = "existing-model"\n')
            (home/'AGENTS.override.md').write_text('Existing instructions.\n')
            (home/'hooks.json').write_text(json.dumps({'hooks':{'Stop':[{'hooks':[{'type':'command','command':'custom-hook'}]}]}}))
            files=installer.connect(home,ROOT)
            before=[p.read_bytes() for p in files]
            installer.connect(home,ROOT)
            self.assertEqual(before,[p.read_bytes() for p in files])
            self.assertIn('Existing instructions.',(home/'AGENTS.override.md').read_text())
            self.assertFalse((home/'AGENTS.md').exists())
            self.assertIn('custom-hook',(home/'hooks.json').read_text())
            self.assertIn('existing-model',(home/'config.toml').read_text())
    def test_invalid_hooks_does_not_partially_write_config(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            (home/'config.toml').write_text('model = "original"\n')
            (home/'hooks.json').write_text('{broken')
            with self.assertRaises(ValueError): installer.connect(home,ROOT)
            self.assertEqual((home/'config.toml').read_text(),'model = "original"\n')
