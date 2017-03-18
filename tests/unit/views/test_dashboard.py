import time

from tests.unit import AsyncHTTPTestCase
from tests.unit.utils import task_succeeded_events, task_failed_events
from tests.unit.utils import HtmlTableParser

from celery.events import Event
from celery.utils import uuid

from flower.events import EventsState


class DashboardTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(DashboardTests, self).get_app()
        super(DashboardTests, self).setUp()

    def get_app(self):
        return self.app

    def test_default_page(self):
        r1 = self.get('/')
        r2 = self.get('/dashboard')
        self.assertEqual(r1.body, r2.body)

    def test_no_workers(self):
        r = self.get('/dashboard')
        self.assertEqual(200, r.code)
        self.assertIn('Load Average', str(r.body))
        self.assertNotIn('<tr id=', str(r.body))

    def test_unknown_worker(self):
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))
        self.assertEqual(['worker1', 'False', '0', '0', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertFalse(table.get_row('worker2'))

    def test_single_workers_online(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        state.event(Event('worker-online', hostname='worker1',
                          local_received=time.time()))
        self.app.events.state = state

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table.rows()))
        self.assertTrue(table.get_row('worker1'))
        self.assertEqual(['worker1', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '1', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '1', '0', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '1', '0', '1', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '1', '1', '0', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '1', '1', '0', '1', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
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

        r = self.get('/dashboard')

        table = HtmlTableParser()
        table.parse(str(r.body))

        self.assertEqual(200, r.code)
        self.assertEqual(3, len(table.rows()))

        self.assertEqual(['worker1', 'True', '0', '100', '0', '100', '0', None],
                         table.get_row('worker1'))
        self.assertEqual(['worker2', 'True', '0', '0', '0', '0', '0', None],
                         table.get_row('worker2'))
        self.assertEqual(['worker3', 'True', '0', '23', '13', '10', '0', None],
                         table.get_row('worker3'))
