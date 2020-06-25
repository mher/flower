import json
import time

from celery.events import Event

from flower.events import EventsState
from tests.unit import AsyncHTTPTestCase
from tests.unit.utils import task_succeeded_events, task_failed_events


class TaskTest(AsyncHTTPTestCase):
    def test_unknown_task(self):
        r = self.get('/task/unknown')
        self.assertEqual(404, r.code)
        self.assertTrue('Unknown task' in str(r.body))


class TasksTest(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(TasksTest, self).get_app()
        super(TasksTest, self).setUp()

    def get_app(self):
        return self.app

    def test_no_task(self):
        r = self.get('/tasks')
        self.assertEqual(200, r.code)
        self.assertTrue('UUID' in str(r.body))
        self.assertNotIn('<tr id=', str(r.body))

    def test_succeeded_task(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='123')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        params = dict(draw=1, start=0, length=10)
        params['search[value]'] = ''
        params['order[0][column]'] = 0
        params['columns[0][data]'] = 'name'
        params['order[0][dir]'] = 'asc'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(1, table['recordsTotal'])
        self.assertEqual(1, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(1, len(tasks))
        self.assertEqual('SUCCESS', tasks[0]['state'])
        self.assertEqual('task1', tasks[0]['name'])
        self.assertEqual('123', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])

    def test_failed_task(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_failed_events(worker='worker1', name='task1',
                                     id='123')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        params = dict(draw=1, start=0, length=10)
        params['search[value]'] = ''
        params['order[0][column]'] = 0
        params['columns[0][data]'] = 'name'
        params['order[0][dir]'] = 'asc'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(1, table['recordsTotal'])
        self.assertEqual(1, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(1, len(tasks))
        self.assertEqual('FAILURE', tasks[0]['state'])
        self.assertEqual('task1', tasks[0]['name'])
        self.assertEqual('123', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])

    def test_sort_runtime(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='2', runtime=10.0)
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='4', runtime=10000000.0)
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='3', runtime=20.0)
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='1', runtime=2.0)
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        params = dict(draw=1, start=0, length=10)
        params['search[value]'] = ''
        params['order[0][column]'] = 0
        params['columns[0][data]'] = 'runtime'
        params['order[0][dir]'] = 'asc'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(4, table['recordsTotal'])
        self.assertEqual(4, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(4, len(tasks))

        self.assertEqual('SUCCESS', tasks[0]['state'])
        self.assertEqual('task1', tasks[0]['name'])
        self.assertEqual('1', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])
        self.assertEqual(2.0, tasks[0]['runtime'])

        self.assertEqual('SUCCESS', tasks[1]['state'])
        self.assertEqual('task1', tasks[1]['name'])
        self.assertEqual('2', tasks[1]['uuid'])
        self.assertEqual('worker1', tasks[1]['worker'])
        self.assertEqual(10.0, tasks[1]['runtime'])

        self.assertEqual('SUCCESS', tasks[3]['state'])
        self.assertEqual('task1', tasks[3]['name'])
        self.assertEqual('4', tasks[3]['uuid'])
        self.assertEqual('worker1', tasks[3]['worker'])
        self.assertEqual(10000000.0, tasks[3]['runtime'])

    def test_sort_incomparable(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='123')
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='456', runtime=None)
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        params = dict(draw=1, start=0, length=10)
        params['search[value]'] = ''
        params['order[0][column]'] = 0
        params['columns[0][data]'] = 'runtime'
        params['order[0][dir]'] = 'asc'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(2, table['recordsTotal'])
        self.assertEqual(2, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(2, len(tasks))

        self.assertEqual('SUCCESS', tasks[0]['state'])
        self.assertEqual('task1', tasks[0]['name'])
        self.assertEqual('456', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])
        self.assertIsNone(tasks[0]['runtime'])

        self.assertEqual('SUCCESS', tasks[1]['state'])
        self.assertEqual('task1', tasks[1]['name'])
        self.assertEqual('123', tasks[1]['uuid'])
        self.assertEqual('worker1', tasks[1]['worker'])

    def test_pagination(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='123')
        events += task_succeeded_events(worker='worker1', name='task2',
                                        id='456')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        params = dict(draw=1, start=0, length=10)
        params['search[value]'] = ''
        params['order[0][column]'] = 0
        params['columns[0][data]'] = 'name'
        params['order[0][dir]'] = 'asc'
        params['start'] = '0'
        params['length'] = '1'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(2, table['recordsTotal'])
        self.assertEqual(2, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(1, len(tasks))

        self.assertEqual('SUCCESS', tasks[0]['state'])
        self.assertEqual('task1', tasks[0]['name'])
        self.assertEqual('123', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])

        params['start'] = '1'
        params['length'] = '1'

        r = self.get('/tasks/datatable?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"))
        self.assertEqual(200, r.code)
        self.assertEqual(2, table['recordsTotal'])
        self.assertEqual(2, table['recordsFiltered'])
        tasks = table['data']
        self.assertEqual(1, len(tasks))

        self.assertEqual('SUCCESS', tasks[0]['state'])
        self.assertEqual('task2', tasks[0]['name'])
        self.assertEqual('456', tasks[0]['uuid'])
        self.assertEqual('worker1', tasks[0]['worker'])
