import io
import json
import unittest
from unittest.mock import MagicMock, patch
from attention_lib.core import herdr_request

class HerdrProtocol(unittest.TestCase):
    def test_native_pane_request(self):
        conn=MagicMock()
        def response(*args):
            payload=json.loads(conn.sendall.call_args.args[0])
            self.assertEqual(payload['method'],'pane.focus')
            self.assertEqual(payload['params'],{'pane_id':'w1:p2'})
            return io.BytesIO((json.dumps({'id':payload['id'],'result':{'type':'pane_focused'}})+'\n').encode())
        conn.makefile.side_effect=response
        with patch('attention_lib.core.socket.socket') as factory:
            factory.return_value.__enter__.return_value=conn
            self.assertEqual(herdr_request('/tmp/test.sock','pane.focus',{'pane_id':'w1:p2'})['type'],'pane_focused')
        conn.connect.assert_called_once_with('/tmp/test.sock')
    def test_error_is_not_acknowledged(self):
        conn=MagicMock()
        conn.makefile.return_value=io.BytesIO(b'{"id":"wrong","error":{"message":"No pane"}}\n')
        with patch('attention_lib.core.socket.socket') as factory:
            factory.return_value.__enter__.return_value=conn
            with self.assertRaises(RuntimeError):herdr_request('/tmp/test.sock','pane.focus',{'pane_id':'w1:p2'})
