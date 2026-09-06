import concurrent.futures
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from attention_lib.core import Queue, proc, validate_target

TARGET = {'kind': 'command', 'argv': ['/usr/bin/true']}

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.q = Queue(self.tmp.name)
    def tearDown(self):
        self.q.db.close(); self.tmp.cleanup()
    def push(self, ident='test', **kwargs):
        return self.q.push('Please approve', os.getpid(), TARGET, ident, **kwargs)
    def test_concurrent_writers(self):
        def writer(i):
            q = Queue(self.tmp.name)
            q.push(str(i), os.getpid(), TARGET, str(i)); q.db.close()
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            list(pool.map(writer, range(40)))
        self.assertEqual(len(self.q.list()), 40)
    def test_dead_owner_removed(self):
        p = subprocess.Popen(['sleep', '10'])
        try: self.q.push('Wait', p.pid, TARGET)
        finally: p.terminate(); p.wait()
        self.assertEqual(self.q.list(), [])
    def test_pid_reuse_removed(self):
        self.push()
        original = proc(os.getpid()); original['start'] = 'different'
        with patch('attention_lib.core.proc', return_value=original):
            self.assertEqual(self.q.list(), [])
    def test_lease_expires(self):
        self.push(ttl=.01); time.sleep(.02)
        self.assertEqual(self.q.list(), [])
    def test_heartbeat(self):
        self.push(ttl=.01); self.q.heartbeat('test', 10); time.sleep(.02)
        self.assertEqual(len(self.q.list()), 1)
    def test_failed_focus_keeps_entry(self):
        self.push()
        with patch('attention_lib.core.focus', side_effect=RuntimeError('missing')):
            with self.assertRaises(RuntimeError): self.q.activate('test')
        self.assertEqual(len(self.q.list()), 1)
    def test_successful_focus_removes(self):
        self.push()
        with patch('attention_lib.core.focus'): self.q.activate('test')
        self.assertEqual(self.q.list(), [])
    def test_replacement_during_focus_survives(self):
        first = self.push()
        with patch('attention_lib.core.focus', side_effect=lambda _: self.push()):
            self.q.activate('test', first['revision'])
        self.assertEqual(len(self.q.list()), 1)
        self.assertNotEqual(self.q.list()[0]['revision'], first['revision'])
    def test_stale_ui_cannot_consume_replacement(self):
        first = self.push(); self.push()
        with self.assertRaises(RuntimeError): self.q.activate('test', first['revision'])
        self.assertEqual(len(self.q.list()), 1)
    def test_nearest_terminal_ancestor(self):
        from attention_lib.core import window_for
        windows=[{'pid':10,'address':'outer'},{'pid':20,'address':'inner'}]
        with patch('attention_lib.core.ancestors',return_value=iter([30,20,10])):
            self.assertEqual(window_for(30,windows)['address'],'inner')
    def test_invalid_targets(self):
        for t in ({'kind': 'window', 'address': 'evil'}, {'kind': 'tmux', 'pane': '-x', 'socket': '/tmp/x'}, {'kind': 'command', 'argv': 'sh -c something'}):
            with self.assertRaises(ValueError): validate_target(t)

if __name__ == '__main__': unittest.main()
