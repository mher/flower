import json
import time
import unittest
from unittest.mock import patch

from celery.events import Event
from celery.utils import uuid

from flower.events import EventsState
from tests.unit import AsyncHTTPTestCase
from tests.unit.utils import (HtmlTableParser, task_failed_events,
                              task_succeeded_events)


class WorkersTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super().get_app()
        super().setUp()

    def get_app(self, capp=None):
        return self.app

    def test_default_page(self):
        r1 = self.get('/')
        r2 = self.get('/workers')
        self.assertEqual(r1.body, r2.body)

    def test_no_workers(self):
        r = self.get('/workers')
        self.assertEqual(200, r.code)
        self.assertIn('Load Average', str(r.body))
        self.assertNotIn('<tr id=', str(r.body))

    @unittest.skip('disable temporarily')
    def test_unknown_worker(self):
        with self.mock_option("inspect_timeout", 1.0):
            r = self.get('/worker/unknown')
            self.assertEqual(404, r.code)
            self.assertIn('Unknown worker', str(r.body))

    def test_single_workers_offline(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        state.event(Event('worker-offline', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        r = self.get('/workers')
        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))
        self.assertEqual(['worker1', None, 'False', '0', '0', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertFalse(table.get_row('worker2'))

    def test_purge_offline_workers(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        state.event(Event('worker-offline', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        with patch('flower.views.workers.options') as mock_options:
            mock_options.purge_offline_workers = 0
            r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(0, len(table.rows()))

    def test_single_workers_online(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time(),
                          ))
        self.app.events.state = state
        self.app.inspector.workers['worker1'] = {'registeres': [],
                                                 'active_queues': [{
                                                     'name': 'default_queue',
                                                     'exchange': {
                                                        'name': 'default',
                                                        'type': 'direct',
                                                        'arguments': None,
                                                        'durable': True,
                                                        'passive': False,
                                                        'auto_delete': False,
                                                        'delivery_mode': None,
                                                        'no_declare': False
                                                 },
                                                 'routing_key': 'default',
                                                 'queue_arguments': None,
                                                 'binding_arguments': None,
                                                 'consumer_arguments': None,
                                                 'durable': True,
                                                 'exclusive': False,
                                                 'auto_delete': False,
                                                 'no_ack': False,
                                                 'alias': None,
                                                 'bindings': [],
                                                 'no_declare': None,
                                                 'expires': None,
                                                 'message_ttl': None,
                                                 'max_length': None,
                                                 'max_length_bytes': None,
                                                 'max_priority': None}],
                                                 'stats': {'total': {'tasks.add': 10, 'tasks.sleep': 1, 'tasks.error': 1},
                                                           'broker': {'hostname': 'redis', 'userid': None, 'virtual_host': '/', 'port': 6379}}}

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))
        self.assertEqual(['worker1', 'default_queue', 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertFalse(table.get_row('worker2'))

    def test_task_received(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2'),
                  Event('task-received', uuid=uuid(), name='task1',
                        args='(2, 2)', kwargs="{'foo': 'bar'}",
                        retries=0, eta=None, hostname='worker1')]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '1', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))

    def test_task_started(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2'),
                  Event('task-received', uuid='123', name='task1',
                        args='(2, 2)', kwargs="{'foo': 'bar'}",
                        retries=0, eta=None, hostname='worker1'),
                  Event('task-started', uuid='123', hostname='worker1')]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '1', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))

    def test_task_succeeded(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2'),
                  Event('task-received', uuid='123', name='task1',
                        args='(2, 2)', kwargs="{'foo': 'bar'}",
                        retries=0, eta=None, hostname='worker1'),
                  Event('task-started', uuid='123', hostname='worker1'),
                  Event('task-succeeded', uuid='123', result='4',
                        runtime=0.1234, hostname='worker1')]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '1', '0', '1', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))

    def test_task_failed(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2'),
                  Event('task-received', uuid='123', name='task1',
                        args='(2, 2)', kwargs="{'foo': 'bar'}",
                        retries=0, eta=None, hostname='worker1'),
                  Event('task-started', uuid='123', hostname='worker1'),
                  Event('task-failed', uuid='123', exception="KeyError('foo')",
                        traceback='line 1 at main', hostname='worker1')]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '1', '1', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))

    def test_task_retried(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2'),
                  Event('task-received', uuid='123', name='task1',
                        args='(2, 2)', kwargs="{'foo': 'bar'}",
                        retries=0, eta=None, hostname='worker1'),
                  Event('task-started', uuid='123', hostname='worker1'),
                  Event('task-retried', uuid='123', exception="KeyError('bar')",
                        traceback='line 2 at main', hostname='worker1'),
                  Event('task-failed', uuid='123', exception="KeyError('foo')",
                        traceback='line 1 at main', hostname='worker1')]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '1', '1', '0', '1', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))

    def test_tasks(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.get_or_create_worker('worker2')
        state.get_or_create_worker('worker3')
        events = [Event('worker-online', hostname='worker1'),
                  Event('worker-online', hostname='worker2')]
        for i in range(100):
            events += task_succeeded_events(worker='worker1')
        for i in range(10):
            events += task_succeeded_events(worker='worker3')
        for i in range(13):
            events += task_failed_events(worker='worker3')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(3, len(table.rows()))

        self.assertEqual(['worker1', None, 'True', '0', '100', '0', '100', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', None, 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))
        self.assertEqual(['worker3', None, 'True', '0', '23', '13', '10', '0', None],
                         table.get_row('worker3'))

    def test_workers_view_json(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        res = self.get('/workers?json=1')
        self.assertEqual(200, res.code)
        data = json.loads(res.body)
        self.assertTrue("data" in data)

    def test_workers_view_refresh(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        with patch.object(self.get_app(), "update_workers") as update_workers_mock:
            res = self.get('/workers?refresh=1')
            self.assertEqual(200, res.code)
            update_workers_mock.assert_called()

    def test_workers_page(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state
        self.app.inspector.workers['worker1'] = {'registeres': [], 'active_queues': [],
                                                 'stats': {'total': {'tasks.add': 10, 'tasks.sleep': 1, 'tasks.error': 1},
                                                           'broker': {'hostname': 'redis', 'userid': None, 'virtual_host': '/', 'port': 6379}}}

        with patch.object(self.get_app(), "update_workers") as update_workers_mock:
            res = self.get('/worker/worker1')
            self.assertEqual(200, res.code)
            update_workers_mock.assert_called_once_with(workername='worker1')

        with patch.object(self.get_app(), "update_workers") as update_workers_mock:
            res = self.get('/worker/worker2')
            self.assertEqual(404, res.code)
            update_workers_mock.assert_called_once_with(workername='worker2')
