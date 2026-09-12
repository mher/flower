import asyncio
import json
import time
from unittest.mock import patch

from celery.events import Event
from celery.utils import uuid

from flower.events import EventsState
from flower.views.workers import WorkerView
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
        self.assertIn('<title>Workers · Flower</title>', r.body.decode('utf-8'))
        self.assertIn('Load Average', str(r.body))
        self.assertNotIn('<tr id=', str(r.body))

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
        self.assertEqual(['worker1', 'False', '0', '0', '0', '0', None],
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

    def test_purge_offline_workers_grace_period(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        state.event(Event('worker-offline', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        with patch('flower.views.workers.options') as mock_options:
            mock_options.purge_offline_workers = 120
            r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))

    def test_single_workers_online(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        r = self.get('/workers')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))
        self.assertEqual(['worker1', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '1', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '1', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '1', '0', '1', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '1', '1', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '1', '1', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
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

        self.assertEqual(['worker1', 'True', '0', '100', '0', '100', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', None],
                         table.get_row('worker2'))
        self.assertEqual(['worker3', 'True', '0', '23', '13', '10', None],
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

    def test_worker_page_waits_for_inspection(self):
        stats = {'total': {'tasks.add': 10},
                 'broker': {'hostname': 'redis', 'userid': None,
                            'virtual_host': '/', 'port': 6379}}

        async def populate(workername=None):
            self.app.inspector.workers[workername]['stats'] = stats

        def inspect(workername=None):
            return asyncio.ensure_future(populate(workername))

        with patch.object(self.get_app(), "update_workers", side_effect=inspect):
            res = self.get('/worker/worker1')
            self.assertEqual(200, res.code)

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
            self.assertIn('<title>worker1 · Flower</title>', res.body.decode('utf-8'))
            update_workers_mock.assert_called_once_with(workername='worker1')

        with patch.object(self.get_app(), "update_workers") as update_workers_mock:
            res = self.get('/worker/worker2')
            self.assertEqual(404, res.code)
            update_workers_mock.assert_called_once_with(workername='worker2')

    def worker_page(self, revoked=(), query=''):
        self.app.inspector.workers['worker1'] = {
            'revoked': list(revoked),
            'stats': {'total': {}, 'broker': {'hostname': 'redis', 'userid': None, 'virtual_host': '/', 'port': 6379}}}
        with patch.object(self.get_app(), "update_workers"):
            return self.get('/worker/worker1' + query)

    def test_long_list_is_cut_to_the_default_limit(self):
        limit = WorkerView.list_limit
        body = self.worker_page(revoked=[f'task-{i}' for i in range(limit + 10)]).body.decode('utf-8')
        self.assertIn(f'task-{limit - 1}<', body)
        self.assertNotIn(f'task-{limit}<', body)

    def test_short_list_is_complete(self):
        body = self.worker_page(revoked=['task-0', 'task-1']).body.decode('utf-8')
        self.assertIn('task-1<', body)

    def test_limit_parameter_raises_the_cut(self):
        body = self.worker_page(revoked=[f'task-{i}' for i in range(60)], query='?limit=60').body.decode('utf-8')
        self.assertIn('task-59<', body)

    def test_limit_parameter_lowers_the_cut(self):
        body = self.worker_page(revoked=[f'task-{i}' for i in range(60)], query='?limit=10').body.decode('utf-8')
        self.assertIn('task-9<', body)
        self.assertNotIn('task-10<', body)

    def test_processed_counts_use_thousands_separators(self):
        self.app.inspector.workers['worker1'] = {
            'stats': {'total': {'tasks.add': 141372}, 'broker': {'hostname': 'redis', 'userid': None, 'virtual_host': '/', 'port': 6379}}}
        with patch.object(self.get_app(), "update_workers"):
            body = self.get('/worker/worker1').body.decode('utf-8')
        self.assertIn('<td>141,372</td>', body)

    def test_invalid_limit_is_rejected(self):
        self.assertEqual(400, self.worker_page(query='?limit=many').code)

    def test_worker_page_waits_for_task_lists(self):
        # stats alone come from the global refresh, the page needs the full inspect
        self.app.inspector.workers['worker1'] = {
            'stats': {'total': {}, 'broker': {'hostname': 'redis', 'userid': None, 'virtual_host': '/', 'port': 6379}}}

        async def populate(workername=None):
            self.app.inspector.workers[workername].update(
                active_queues=[], registered=[], conf={}, scheduled=[], active=[], reserved=[],
                revoked=['task-from-full-inspect'])

        with patch.object(self.get_app(), "update_workers", side_effect=lambda workername=None: asyncio.ensure_future(populate(workername))):
            body = self.get('/worker/worker1').body.decode('utf-8')

        self.assertIn('task-from-full-inspect', body)
