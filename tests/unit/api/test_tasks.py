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
    def reapply(self, mock_task, taskid='123',
                send_task_result=AsyncResult('new-task-id')):
        """POST /api/task/reapply with mocked event state and send_task."""
        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            with patch.object(self._app.capp, 'send_task',
                              return_value=send_task_result) as send_task:
                r = self.post(f'/api/task/reapply/{taskid}', body='')
        return r, send_task

    def test_reapply_success(self):
        """Test successfully reapplying a task"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{"multiply": 2}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertIn('task-id', body)
        send_task.assert_called_once_with(
            'tasks.add', args=[1, 2], kwargs={"multiply": 2}
        )

    def test_reapply_task_not_found(self):
        """Test reapplying a non-existent task returns 404"""
        r, send_task = self.reapply(None, taskid='nonexistent')

        self.assertEqual(404, r.code)
        send_task.assert_not_called()

    def test_reapply_task_no_name(self):
        """Test reapplying a task with no name returns 400"""
        mock_task = Task()
        mock_task.name = None

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_unregistered_task(self):
        """Test a task not registered in flower's app is still reapplied

        Flower often runs without the application's task modules being
        importable; send_task does not require local registration.
        """
        mock_task = Task()
        mock_task.name = 'unknown.task'
        mock_task.args = '[]'
        mock_task.kwargs = '{}'

        self.assertNotIn('unknown.task', self._app.capp.tasks)
        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with('unknown.task', args=[], kwargs={})

    def test_reapply_preserves_routing(self):
        """Test the original routing_key/exchange are reused when present"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'
        mock_task.routing_key = 'high.priority'
        mock_task.exchange = 'tasks'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with(
            'tasks.add', args=[1, 2], kwargs={},
            routing_key='high.priority', exchange='tasks'
        )

    def test_reapply_invalid_args(self):
        """Test reapplying a task with unparseable args returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = 'invalid json'
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_truncated_args(self):
        """Test reapplying a task whose args repr was truncated returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = "(1, 2, 'long-value..."
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_truncated_string_arg(self):
        """Test a string arg truncated inside its quotes by celery returns 400

        saferepr can truncate long strings while keeping the repr parseable,
        e.g. "(7, 'Bearer...')" for a long token.
        """
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = "(7, 'Bearer...')"
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_deeply_nested_args(self):
        """Test pathologically nested args return 400, not a 500"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[' * 3000
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_non_list_args(self):
        """Test reapplying a task whose args are not a list/tuple returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '"just a string"'
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_non_dict_kwargs(self):
        """Test reapplying a task whose kwargs are not a dict returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[]'
        mock_task.kwargs = '[1, 2]'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_non_serializable_args(self):
        """Test reapplying a task with non-JSON-serializable args returns 400"""
        for bad_args in ("(b'raw-bytes',)", '({1, 2},)'):
            mock_task = Task()
            mock_task.name = 'tasks.add'
            mock_task.args = bad_args
            mock_task.kwargs = '{}'

            r, send_task = self.reapply(mock_task)

            self.assertEqual(400, r.code, bad_args)
            send_task.assert_not_called()

    def test_reapply_non_string_dict_keys(self):
        """Test kwargs with non-string dict keys return 400"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[]'
        mock_task.kwargs = "{'mapping': {1: 'a'}}"

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_send_task_error(self):
        """Test handling error during send_task returns 500"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
            with patch.object(self._app.capp, 'send_task',
                              side_effect=Exception("Connection error")):
                r = self.post('/api/task/reapply/123', body='')

        self.assertEqual(500, r.code)

    def test_reapply_with_empty_args(self):
        """Test reapplying a task with empty args"""
        mock_task = Task()
        mock_task.name = 'tasks.simple'
        mock_task.args = ''
        mock_task.kwargs = ''

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with('tasks.simple', args=[], kwargs={})

    def test_reapply_with_ellipsis_args(self):
        """Test reapplying a task with truncated ('...') args returns 400"""
        mock_task = Task()
        mock_task.name = 'tasks.test'
        mock_task.args = '...'
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(400, r.code)
        send_task.assert_not_called()

    def test_reapply_with_nested_json_args(self):
        """Test reapplying task with nested JSON structures in args"""
        mock_task = Task()
        mock_task.name = 'tasks.process'
        mock_task.args = '[{"user_id": 123, "items": [1, 2, 3]}, "action"]'
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with(
            'tasks.process',
            args=[{"user_id": 123, "items": [1, 2, 3]}, "action"],
            kwargs={}
        )

    def test_reapply_with_complex_kwargs(self):
        """Test reapplying task with complex JSON in kwargs"""
        mock_task = Task()
        mock_task.name = 'tasks.configure'
        mock_task.args = '[]'
        mock_task.kwargs = '{"retry": true, "timeout": 30, "options": {"key": "value"}}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with(
            'tasks.configure',
            args=[],
            kwargs={"retry": True, "timeout": 30, "options": {"key": "value"}}
        )

    def test_reapply_with_python_tuple_args(self):
        """Test reapplying task with Python tuple string in args"""
        mock_task = Task()
        mock_task.name = 'tasks.tuple_task'
        mock_task.args = '(1, 2, 3)'
        mock_task.kwargs = '{}'

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with('tasks.tuple_task', args=[1, 2, 3], kwargs={})

    def test_reapply_with_python_dict_kwargs(self):
        """Test reapplying task with Python dict string in kwargs"""
        mock_task = Task()
        mock_task.name = 'tasks.dict_task'
        mock_task.args = '[]'
        mock_task.kwargs = "{'count': 5, 'enabled': True}"

        r, send_task = self.reapply(mock_task)

        self.assertEqual(200, r.code)
        send_task.assert_called_once_with(
            'tasks.dict_task',
            args=[],
            kwargs={'count': 5, 'enabled': True}
        )

    def test_reapply_json_serialization_in_response(self):
        """Test that response is properly JSON serialized"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        r, _ = self.reapply(mock_task, send_task_result=AsyncResult('test-task-123'))

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
