import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from unittest.mock import Mock, PropertyMock, patch

import celery.states as states
from celery.events import Event
from celery.events.state import Task
from celery.result import AsyncResult

from flower.events import EventsState
from tests.unit.utils import task_succeeded_events

from . import BaseApiTestCase


class ApplyTests(BaseApiTestCase):
    def test_apply(self):
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


class AsyncApplyTests(BaseApiTestCase):
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


class TaskReapplyTests(BaseApiTestCase):
    def test_reapply_success(self):
        """Test successfully reapplying a task"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{"multiply": 2}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.add'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertIn('task-id', body)
        task.apply_async.assert_called_once_with(
            args=[1, 2], kwargs={"multiply": 2}
        )

    def test_reapply_task_not_found(self):
        """Test reapplying a non-existent task returns 404"""
        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=None):
            r = self.post('/api/task/reapply/nonexistent', body='')

        self.assertEqual(404, r.code)

    def test_reapply_task_no_name(self):
        """Test reapplying a task with no name returns 400"""
        mock_task = Task()
        mock_task.name = None

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(400, r.code)

    def test_reapply_unknown_task_name(self):
        """Test reapplying a task that is not registered returns 404"""
        mock_task = Task()
        mock_task.name = 'unknown.task'
        mock_task.args = '[]'
        mock_task.kwargs = '{}'

        if 'unknown.task' in self._app.capp.tasks:
            del self._app.capp.tasks['unknown.task']

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(404, r.code)

    def test_reapply_invalid_args(self):
        """Test reapplying a task with invalid args returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = 'invalid json'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            self._app.capp.tasks['tasks.add'] = Mock()
            with patch('flower.api.tasks.parse_args', side_effect=ValueError("Invalid args")):
                r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(400, r.code)

    def test_reapply_apply_async_error(self):
        """Test handling error during apply_async returns 500"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.add'] = Mock()
            task.apply_async = Mock(side_effect=Exception("Connection error"))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(500, r.code)

    def test_reapply_with_empty_args(self):
        """Test reapplying a task with empty args"""
        mock_task = Task()
        mock_task.name = 'tasks.simple'
        mock_task.args = ''
        mock_task.kwargs = ''

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.simple'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(args=[], kwargs={})

    def test_reapply_with_ellipsis_args(self):
        """Test reapplying a task with ellipsis in args"""
        mock_task = Task()
        mock_task.name = 'tasks.test'
        mock_task.args = '...'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.test'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(args=[None], kwargs={})

    def test_reapply_with_nested_json_args(self):
        """Test reapplying task with nested JSON structures in args"""
        mock_task = Task()
        mock_task.name = 'tasks.process'
        mock_task.args = '[{"user_id": 123, "items": [1, 2, 3]}, "action"]'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.process'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[{"user_id": 123, "items": [1, 2, 3]}, "action"],
            kwargs={}
        )

    def test_reapply_with_complex_kwargs(self):
        """Test reapplying task with complex JSON in kwargs"""
        mock_task = Task()
        mock_task.name = 'tasks.configure'
        mock_task.args = '[]'
        mock_task.kwargs = '{"retry": true, "timeout": 30, "options": {"key": "value"}}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.configure'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[],
            kwargs={"retry": True, "timeout": 30, "options": {"key": "value"}}
        )

    def test_reapply_with_python_tuple_args(self):
        """Test reapplying task with Python tuple string in args"""
        mock_task = Task()
        mock_task.name = 'tasks.tuple_task'
        mock_task.args = '(1, 2, 3)'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.tuple_task'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(args=(1, 2, 3), kwargs={})

    def test_reapply_with_python_dict_kwargs(self):
        """Test reapplying task with Python dict string in kwargs"""
        mock_task = Task()
        mock_task.name = 'tasks.dict_task'
        mock_task.args = '[]'
        mock_task.kwargs = "{'count': 5, 'enabled': True}"

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.dict_task'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('new-task-id'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[],
            kwargs={'count': 5, 'enabled': True}
        )

    def test_reapply_json_serialization_in_response(self):
        """Test that response is properly JSON serialized"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            task = self._app.capp.tasks['tasks.add'] = Mock()
            task.apply_async = Mock(return_value=AsyncResult('test-task-123'))
            r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertIn('task-id', body)
        self.assertEqual(body['task-id'], 'test-task-123')

        self.assertIsInstance(body, dict)


class TaskTests(BaseApiTestCase):
    def setUp(self):
        self.app = super().get_app()
        super().setUp()

    def get_app(self, capp=None):
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
        lastFetchedTaskName = table[list(table)[-1]]['name']
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
        lastFetchedTaskName = table[list(table)[-1]]['name']
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
        lastFetchedTaskName = table[list(table)[-1]]['name']
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
        lastFetchedTaskName = table[list(table)[-1]]['name']
        self.assertEqual("task2", firstFetchedTaskName)
        self.assertEqual("task3", lastFetchedTaskName)

        # Test limit 4 with search
        params = dict(limit=4, offset=0, sort_by='name', search='task')

        r = self.get('/api/tasks?' + '&'.join(
            map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        lastFetchedTaskName = table[list(table)[-1]]['name']
        self.assertEqual("task1", firstFetchedTaskName)
        self.assertEqual("task4", lastFetchedTaskName)

        # Test limit 4 with search
        params = dict(limit=4, offset=0, sort_by='name', search='task1')

        r = self.get('/api/tasks?' + '&'.join(
            map(lambda x: '%s=%s' % x, params.items())))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table))
        firstFetchedTaskName = table[list(table)[0]]['name']
        self.assertEqual("task1", firstFetchedTaskName)
