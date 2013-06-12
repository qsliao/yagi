import functools
import unittest

import requests
import stubout
import json

import yagi.config

from yagi.handler.stacktach_ping_handler import StackTachPing


class MockResponse(object):
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.text = "Ka-Splat!!"


class MockMessage(object):
    def __init__(self, payload):
        self.payload = payload
        self.acknowledged = False

    def ack(self):
        self.acknowledged = True


class StackTachPingTests(unittest.TestCase):
    """Tests to ensure the Stachtach ping handler works"""

    def setUp(self):
        self.stubs = stubout.StubOutForTesting()
        config_dict = {
            'stacktach': {
                'url': 'http://127.0.0.1:9000/db/confirm/usage/exists/batch',
                'timeout': '120',
            },
        }

        self.handler = StackTachPing()

        def get(*args, **kwargs):
            val = None
            for arg in args:
                if val:
                    val = val.get(arg)
                else:
                    val = config_dict.get(arg)
                    if not val:
                        return None or kwargs.get('default')
            return val

        def config_with(*args):
            return functools.partial(get, args)

        self.stubs.Set(yagi.config, 'config_with', config_with)
        self.stubs.Set(yagi.config, 'get', get)

    def tearDown(self):
        self.stubs.UnsetAll()

    def test_ping(self):
        messages = [MockMessage({'event_type': 'compute.instance.create',
                    'message_id': '1',
                    'content': dict(a=3)}),
                    MockMessage({'event_type': 'compute.instance.delete',
                    'message_id': '2',
                    'content': dict(a=42)}),
                    ]

        self.called = False
        self.data = None

        def mock_put(url, data=None, **kw):
            self.called = True
            self.data = data
            return MockResponse(201)

        mock_env = {'atompub.results':
                      {'1' : dict(code=201, error=False, message="yay"),
                       '2' : dict(code=404, error=False, message="boo")}}

        self.stubs.Set(requests, 'put', mock_put)
        self.stubs.Set(requests.codes, 'ok', 201)

        self.handler.handle_messages(messages, mock_env)
        self.assertTrue(self.called)
        val = json.loads(self.data)
        self.assertTrue('messages' in val)
        self.assertEqual(len(val['messages']), 2)
        self.assertEqual(val['messages']['1'], 201)
        self.assertEqual(val['messages']['2'], 404)

    def test_ping_fails(self):
        #make sure it doesn't blow up if stacktach is borked.
        messages = [MockMessage({'event_type': 'compute.instance.create',
                    'message_id': '1',
                    'content': dict(a=3)}),
                    MockMessage({'event_type': 'compute.instance.delete',
                    'message_id': '2',
                    'content': dict(a=42)}),
                    ]

        self.called = False
        self.data = None

        def mock_put(url, data=None, **kw):
            self.called = True
            self.data = data
            return MockResponse(500)

        mock_env = {'atompub.results':
                      {'1' : dict(code=201, error=False, message="yay"),
                       '2' : dict(code=404, error=False, message="boo")}}

        self.stubs.Set(requests, 'put', mock_put)
        self.stubs.Set(requests.codes, 'ok', 201)

        self.handler.handle_messages(messages, mock_env)
        self.assertTrue(self.called)
