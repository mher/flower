import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, PropertyMock, patch
from urllib.parse import urlencode

from celery import states
from celery.events import Event
from celery.events.state import Task
from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.result import AsyncResult
from kombu.exceptions import OperationalError
from tornado.options import options

from flower.events import EventsState
from tests.unit.utils import task_succeeded_events

from . import BaseApiTestCase


class ApplyTests(BaseApiTestCase):
    def test_apply(self):
        for args, kwargs in (
                ([], {}),
                ([7, 'customer-42'], {'notify': True, 'label': '<order> & "quoted"'})):
            with self.subTest(args=args, kwargs=kwargs):
                ar = Mock(spec=AsyncResult, task_id='applied-task-id',
                          state=states.SUCCESS, result='result',
                          backend=Mock(connection_errors=()))
                task = self._app.capp.tasks['foo'] = Mock()
                task.apply_async.return_value = ar

                body = json.dumps({'args': args, 'kwargs': kwargs}) if args or kwargs else ''
                r = self.post('/api/task/apply/foo', body=body,
                              headers={'Content-Type': 'application/json'})

                self.assertEqual(200, r.code)
                self.assertEqual({'task-id': 'applied-task-id',
                                  'state': states.SUCCESS, 'result': 'result'},
                                 json.loads(r.body))
                task.apply_async.assert_called_once_with(args=args, kwargs=kwargs)
                ar.get.assert_called_once_with(propagate=False, timeout=None)

    def test_apply_unserializable_result_returns_repr(self):
        result = object()
        with (
            patch('celery.result.AsyncResult.state', new_callable=PropertyMock) as mock_state,
            patch('celery.result.AsyncResult.result', new_callable=PropertyMock) as mock_result,
        ):
            mock_state.return_value = states.SUCCESS
            mock_result.return_value = result

            ar = AsyncResult(123)
            ar.get = Mock(return_value=result)

            task = self._app.capp.tasks['foo'] = Mock()
            task.apply_async = Mock(return_value=ar)

            r = self.post('/api/task/apply/foo', body='')

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertEqual(repr(result), body['result'])

    def test_apply_timeout_expiry_returns_state(self):
        with patch('celery.result.AsyncResult.state', new_callable=PropertyMock) as mock_state:
            mock_state.return_value = states.PENDING

            ar = AsyncResult(123)
            ar.get = Mock(side_effect=CeleryTimeoutError())

            task = self._app.capp.tasks['foo'] = Mock()
            task.apply_async = Mock(return_value=ar)

            r = self.post('/api/task/apply/foo', body='{"timeout": 0.1}')

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertEqual(states.PENDING, body['state'])
        self.assertNotIn('result', body)
        ar.get.assert_called_once_with(propagate=False, timeout=0.1)
        task.apply_async.assert_called_once_with(args=[], kwargs={})

    def test_apply_invalid_timeout(self):
        task = self._app.capp.tasks['foo'] = Mock()

        r = self.post('/api/task/apply/foo', body='{"timeout": "abc"}')

        self.assertEqual(400, r.code)
        task.apply_async.assert_not_called()

    def test_apply_read_only(self):
        with patch.object(options.mockable(), 'read_only', True):
            celery = self._app.capp
            celery.tasks['foo'] = Mock()
            celery.tasks['foo'].apply_async = MagicMock()
            r = self.post('/api/task/apply/foo', body='')
            self.assertEqual(403, r.code)
            celery.tasks['foo'].apply_async.assert_not_called()


class AsyncApplyTests(BaseApiTestCase):
    def test_async_apply(self):
        for args, kwargs in (
                ([], {}),
                ([7, 'customer-42'], {'notify': True, 'label': '<order> & "quoted"'})):
            with self.subTest(args=args, kwargs=kwargs):
                result = Mock(spec=AsyncResult, task_id='async-task-id',
                              state=states.PENDING,
                              backend=Mock(connection_errors=()))
                task = self._app.capp.tasks['foo'] = Mock()
                task.apply_async.return_value = result

                body = json.dumps({'args': args, 'kwargs': kwargs}) if args or kwargs else ''
                r = self.post('/api/task/async-apply/foo', body=body,
                              headers={'Content-Type': 'application/json'})

                self.assertEqual(200, r.code)
                self.assertEqual({'task-id': 'async-task-id', 'state': states.PENDING},
                                 json.loads(r.body))
                task.apply_async.assert_called_once_with(args=args, kwargs=kwargs)
                result.get.assert_not_called()

    def test_broker_connection_failure_returns_service_unavailable(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async.side_effect = OperationalError('broker is down')

        r = self.post('/api/task/async-apply/foo', body={})

        self.assertEqual(503, r.code)

    def test_async_apply_eta(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        tomorrow = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        r = self.post('/api/task/async-apply/foo',
                      body=json.dumps({'eta': str(tomorrow)}))

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
        tomorrow = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
        r = self.post('/api/task/async-apply/foo',
                      body=json.dumps({'expires': str(tomorrow)}))

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(
            args=[], kwargs={}, expires=tomorrow)

    def test_async_apply_read_only(self):
        with patch.object(options.mockable(), 'read_only', True):
            celery = self._app.capp
            celery.tasks['foo'] = Mock()
            celery.tasks['foo'].apply_async = MagicMock()
            r = self.post('/api/task/async-apply/foo', body={})
            self.assertEqual(403, r.code)
            celery.tasks['foo'].apply_async.assert_not_called()


class SendTaskTests(BaseApiTestCase):
    def test_send_task(self):
        for args, kwargs in (
                ([], {}),
                ([7, 'customer-42'], {'notify': True, 'label': '<order> & "quoted"'})):
            with self.subTest(args=args, kwargs=kwargs):
                result = Mock(spec=AsyncResult, task_id='sent-task-id',
                              state=states.PENDING,
                              backend=Mock(connection_errors=()))
                self._app.capp.send_task = Mock(return_value=result)

                body = json.dumps({'args': args, 'kwargs': kwargs}) if args or kwargs else ''
                r = self.post('/api/task/send-task/foo', body=body,
                              headers={'Content-Type': 'application/json'})

                self.assertEqual(200, r.code)
                self.assertEqual({'task-id': 'sent-task-id', 'state': states.PENDING},
                                 json.loads(r.body))
                self._app.capp.send_task.assert_called_once_with(
                    'foo', args=args, kwargs=kwargs)
                result.get.assert_not_called()

    def test_broker_connection_failure_returns_service_unavailable(self):
        self._app.capp.send_task = Mock(
            side_effect=OperationalError('broker is down'))

        r = self.post('/api/task/send-task/foo', body={})

        self.assertEqual(503, r.code)


class TaskPublishValidationTests(BaseApiTestCase):
    def assert_invalid_request(self, body, error=None):
        for route in ('apply', 'async-apply', 'send-task'):
            with self.subTest(route=route, body=body):
                task = self._app.capp.tasks['foo'] = Mock()
                self._app.capp.send_task = Mock()

                r = self.post(f'/api/task/{route}/foo', body=body,
                              headers={'Content-Type': 'application/json'})

                self.assertEqual(400, r.code)
                if error is not None:
                    self.assertIn(error, r.body.decode('utf-8'))
                task.apply_async.assert_not_called()
                self._app.capp.send_task.assert_not_called()

    def test_malformed_json_is_not_published(self):
        for body in ('{', '{"args": [1,]}', '{"args": [1]'):
            self.assert_invalid_request(body)

    def test_non_object_body_is_not_published(self):
        for payload in ([], None, 'not-an-object', 42, True):
            self.assert_invalid_request(json.dumps(payload), 'invalid options')

    def test_invalid_args_are_not_published(self):
        for args in (None, False, 42, 'not-an-array', {'key': 'value'}):
            self.assert_invalid_request(json.dumps({'args': args}), 'args must be an array')


class TaskResultTests(BaseApiTestCase):
    @patch('flower.api.tasks.AsyncResult')
    def test_backend_connection_failure_returns_service_unavailable(
            self, async_result):
        class BackendConnectionError(Exception):
            pass

        result = Mock()
        result.backend.connection_errors = (BackendConnectionError,)
        type(result).state = PropertyMock(
            side_effect=BackendConnectionError('backend is down'))
        async_result.return_value = result

        r = self.get('/api/task/result/123')

        self.assertEqual(503, r.code)


class TaskResultTimeoutExpiryTests(BaseApiTestCase):
    @patch('flower.api.tasks.AsyncResult')
    def test_timeout_expiry_returns_state(self, async_result):
        result = Mock()
        result.id = '123'
        result.state = states.STARTED
        result.backend.connection_errors = ()
        result.get.side_effect = CeleryTimeoutError()
        async_result.return_value = result

        r = self.get('/api/task/result/123?timeout=1')

        self.assertEqual(200, r.code)
        body = json.loads(r.body.decode('utf-8'))
        self.assertEqual(states.STARTED, body['state'])
        self.assertNotIn('result', body)


class TaskResultInvalidTimeoutTests(BaseApiTestCase):
    def test_invalid_timeout(self):
        r = self.get('/api/task/result/123?timeout=abc')

        self.assertEqual(400, r.code)
        self.assertIn('Invalid argument', r.body.decode('utf-8'))


class QueueLengthsTests(BaseApiTestCase):
    @patch('flower.views.Broker', side_effect=NotImplementedError)
    def test_unsupported_broker(self, _broker):
        r = self.get('/api/queues/length')

        self.assertEqual(404, r.code)
        self.assertIn('broker is not supported', r.body.decode('utf-8'))


class TaskAbortTests(BaseApiTestCase):
    @patch('flower.api.tasks.AbortableAsyncResult')
    def test_backend_connection_failure_returns_service_unavailable(
            self, abortable_result):
        result = Mock()
        result.backend.connection_errors = (ConnectionError,)
        result.abort.side_effect = ConnectionError('backend is down')
        abortable_result.return_value = result

        r = self.post('/api/task/abort/123', body={})

        self.assertEqual(503, r.code)


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

    def test_reapply_read_only(self):
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        with patch.object(options.mockable(), 'read_only', True):
            r, send_task = self.reapply(mock_task)

        self.assertEqual(403, r.code)
        send_task.assert_not_called()

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
        """Test broker outages return 503 and other send errors 500"""
        mock_task = Task()
        mock_task.name = 'tasks.add'
        mock_task.args = '[1, 2]'
        mock_task.kwargs = '{}'

        for error, code in ((OperationalError('broker down'), 503),
                            (Exception('boom'), 500)):
            with patch('flower.api.tasks.tasks.get_task_by_id', return_value=mock_task):
                with patch.object(self._app.capp, 'send_task', side_effect=error):
                    r = self.post('/api/task/reapply/123', body='')

            self.assertEqual(code, r.code, error)

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
    def test_task_info(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1', id='123')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        r = self.get('/api/task/info/123')

        self.assertEqual(200, r.code)
        info = json.loads(r.body)
        self.assertEqual('123', info['uuid'])
        self.assertEqual('task1', info['name'])
        self.assertEqual(states.SUCCESS, info['state'])
        self.assertEqual('(2, 2)', info['args'])
        self.assertEqual("{'foo': 'bar'}", info['kwargs'])
        self.assertEqual('4', info['result'])
        self.assertEqual(0.1234, info['runtime'])
        self.assertEqual('worker1', info['worker'])

    def test_unknown_task_error_preserves_percent(self):
        r = self.get('/api/task/info/foo%25bar')

        self.assertEqual(404, r.code)
        self.assertIn("Unknown task 'foo%bar'", r.body.decode('utf-8'))

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

        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        # Test limit 4 and offset 0
        params = {'limit': 4, 'offset': 0, 'sort_by': 'name'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task1", names[0])
        self.assertEqual("task4", names[-1])

        # Test limit 4 and offset 1
        params = {'limit': 4, 'offset': 1, 'sort_by': 'name'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(3, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task2", names[0])
        self.assertEqual("task4", names[-1])

        # Test limit 4 and offset -1 (-1 should act as 0)
        params = {'limit': 4, 'offset': -1, 'sort_by': 'name'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task1", names[0])
        self.assertEqual("task4", names[-1])

        # Test limit 2 and offset 1
        params = {'limit': 2, 'offset': 1, 'sort_by': 'name'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(2, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task2", names[0])
        self.assertEqual("task3", names[-1])

        # Test limit 4 with search
        params = {'limit': 4, 'offset': 0, 'sort_by': 'name', 'search': 'task'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(4, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task1", names[0])
        self.assertEqual("task4", names[-1])

        # Test limit 4 with search
        params = {'limit': 4, 'offset': 0, 'sort_by': 'name', 'search': 'task1'}

        r = self.get('/api/tasks?' + '&'.join(
            '{}={}'.format(*x) for x in params.items()))

        table = json.loads(r.body.decode("utf-8"), object_pairs_hook=OrderedDict)

        self.assertEqual(200, r.code)
        self.assertEqual(1, len(table))
        names = [task['name'] for task in table.values()]
        self.assertEqual("task1", names[0])

    def test_invalid_sort_by(self):
        r = self.get('/api/tasks?sort_by=bogus')

        self.assertEqual(400, r.code)
        self.assertIn('Invalid sort_by', r.body.decode('utf-8'))

    def seed_tasks_received_at(self, received):
        # insertion order differs from both sort orders so the sort has to do the work
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        for task_id, timestamp in received.items():
            for e in task_succeeded_events(worker='worker1', name='task', id=task_id):
                e['timestamp'] = timestamp
                events.append(e)
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

    def sorted_task_ids(self, query):
        r = self.get('/api/tasks?' + query)
        self.assertEqual(200, r.code)
        return list(json.loads(r.body, object_pairs_hook=OrderedDict))

    def test_valid_sort_by_ascending(self):
        self.seed_tasks_received_at({'b': 200.0, 'a': 100.0, 'c': 300.0})

        self.assertEqual(['a', 'b', 'c'], self.sorted_task_ids('sort_by=received'))
        self.assertEqual(['a', 'b'], self.sorted_task_ids('sort_by=received&limit=2'))
        self.assertEqual(['b', 'c'], self.sorted_task_ids('sort_by=received&limit=2&offset=1'))

    def test_valid_sort_by_descending(self):
        self.seed_tasks_received_at({'b': 200.0, 'a': 100.0, 'c': 300.0})

        self.assertEqual(['c', 'b', 'a'], self.sorted_task_ids('sort_by=-received'))
        self.assertEqual(['c', 'b'], self.sorted_task_ids('sort_by=-received&limit=2'))
        self.assertEqual(['b', 'a'], self.sorted_task_ids('sort_by=-received&limit=2&offset=1'))

    def test_invalid_limit(self):
        r = self.get('/api/tasks?limit=xyz')

        self.assertEqual(400, r.code)

    def test_invalid_received_start(self):
        r = self.get('/api/tasks?received_start=garbage')

        self.assertEqual(400, r.code)
        self.assertIn('received_start', r.body.decode('utf-8'))

    def test_search_with_quoted_phrase(self):
        state = EventsState()
        for uuid, args in (('1', ['hello world']), ('2', ['hello there'])):
            state.event(Event(
                'task-received', uuid=uuid, name='task1', args=args, kwargs={},
                retries=0, eta=None, hostname='worker1', clock=int(uuid),
                local_received=time.time()))
        self._app.events.state = state

        r = self.get('/api/tasks?' + urlencode({'search': 'args:"hello world"'}))

        self.assertEqual(200, r.code)
        self.assertEqual(['1'], list(json.loads(r.body.decode('utf-8'))))

    def test_invalid_search(self):
        r = self.get('/api/tasks?search=ab')

        self.assertEqual(400, r.code)
        error = json.loads(r.body.decode('utf-8'))
        self.assertEqual(
            'Substring search terms must contain at least 3 characters '
            'at position 0.',
            error['error'])
