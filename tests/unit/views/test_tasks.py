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
