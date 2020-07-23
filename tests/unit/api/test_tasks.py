from mock import Mock, patch
from datetime import datetime, timedelta

from celery.result import AsyncResult
import celery.states as states

from tests.unit import AsyncHTTPTestCase
from flower.events import EventsState
from celery.events import Event

from tests.unit.utils import task_succeeded_events
import json
import time
from collections import OrderedDict


class ApplyTests(AsyncHTTPTestCase):
    def test_apply(self):
        from mock import patch, PropertyMock
        import json

        result = 'result'
        with patch('celery.result.AsyncResult.state', new_callable=PropertyMock) as mock_state:
            with patch('celery.result.AsyncResult.result', new_callable=PropertyMock) as mock_result:
                mock_state.return_value = states.SUCCESS
                mock_result.return_value = result

                ar = AsyncResult(123)
                ar.get = Mock(return_value=result)

                task = self._app.capp.tasks['foo'] = Mock()
                task.apply_async = Mock(return_value=ar)

                r = self.post('/api/task/apply/foo', body='')

        self.assertEqual(200, r.code)
        body = bytes.decode(r.body)
        self.assertEqual(result, json.loads(body)['result'])
        task.apply_async.assert_called_once_with(args=[], kwargs={})


class AsyncApplyTests(AsyncHTTPTestCase):
    def test_async_apply(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        r = self.post('/api/task/async-apply/foo', body={})

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(args=[], kwargs={})

    def test_async_apply_eta(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        tomorrow = datetime.utcnow() + timedelta(days=1)
        r = self.post('/api/task/async-apply/foo',
                      body='{"eta": "%s"}' % tomorrow)

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[], kwargs={}, eta=tomorrow)

    def test_async_apply_countdown(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        r = self.post('/api/task/async-apply/foo',
                      body='{"countdown": "3"}')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[], kwargs={}, countdown=3)

    def test_async_apply_expires(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        r = self.post('/api/task/async-apply/foo',
                      body='{"expires": "60"}')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[], kwargs={}, expires=60)

    def test_async_apply_expires_datetime(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        tomorrow = datetime.utcnow() + timedelta(days=1)
        r = self.post('/api/task/async-apply/foo',
                      body='{"expires": "%s"}' % tomorrow)

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[], kwargs={}, expires=tomorrow)


class MockTasks:

    @staticmethod
    def get_task_by_id(events, task_id):
        from celery.events.state import Task
        return Task()


class TaskTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(TaskTests, self).get_app()
        super(TaskTests, self).setUp()

    def get_app(self):
        return self.app

    @patch('flower.api.tasks.tasks', new=MockTasks)
    def test_task_info(self):
        self.get('/api/task/info/123')

    def test_tasks_pagination(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1',
                                        id='123')
        events += task_succeeded_events(worker='worker1', name='task2',
                                        id='456')
        events += task_succeeded_events(worker='worker1', name='task3',
                                        id='789')
        events += task_succeeded_events(worker='worker1', name='task4',
                                        id='666')
                                        
        # for i, e in enumerate(sorted(events, key=lambda event: event['uuid'])):
        
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        # Test limit 4 and offset 0
        params = dict(limit=4, offset=0, sort_by='name')

        r = self.get('/api/tasks?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        lastFetchedTaskName =  table[list(table)[-1]]['name']
        self.assertEqual("task1", firstFetchedTaskName)
        self.assertEqual("task4", lastFetchedTaskName)

        # Test limit 4 and offset 1
        params = dict(limit=4, offset=1, sort_by='name')

        r = self.get('/api/tasks?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(3, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        lastFetchedTaskName =  table[list(table)[-1]]['name']
        self.assertEqual("task2", firstFetchedTaskName)
        self.assertEqual("task4", lastFetchedTaskName)

        # Test limit 4 and offset -1 (-1 should act as 0)
        params = dict(limit=4, offset=-1, sort_by="name")

        r = self.get('/api/tasks?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        lastFetchedTaskName =  table[list(table)[-1]]['name']
        self.assertEqual("task1", firstFetchedTaskName)
        self.assertEqual("task4", lastFetchedTaskName)

        # Test limit 2 and offset 1
        params = dict(limit=2, offset=1, sort_by='name')

        r = self.get('/api/tasks?' + '&'.join(
                        map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        lastFetchedTaskName =  table[list(table)[-1]]['name']
        self.assertEqual("task2", firstFetchedTaskName)
        self.assertEqual("task3", lastFetchedTaskName)

