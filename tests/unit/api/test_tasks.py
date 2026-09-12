import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, PropertyMock, patch
from urllib.parse import urlencode

import celery.states as states
from celery.events import Event
from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.result import AsyncResult
from kombu.exceptions import OperationalError
from tornado.options import options

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

    def test_apply_unserializable_result_returns_repr(self):
        result = object()
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
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async = Mock(return_value=AsyncResult(123))
        r = self.post('/api/task/async-apply/foo', body={})

        self.assertEqual(200, r.code)
        task.apply_async.assert_called_once_with(args=[], kwargs={})

    def test_broker_connection_failure_returns_service_unavailable(self):
        task = self._app.capp.tasks['foo'] = Mock()
        task.apply_async.side_effect = OperationalError('broker is down')

        r = self.post('/api/task/async-apply/foo', body={})

        self.assertEqual(503, r.code)

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
        result = AsyncResult(123)
        self._app.capp.send_task = Mock(return_value=result)

        r = self.post('/api/task/send-task/foo', body={})

        self.assertEqual(200, r.code)
        self._app.capp.send_task.assert_called_once_with(
            'foo', args=[], kwargs={})

    def test_broker_connection_failure_returns_service_unavailable(self):
        self._app.capp.send_task = Mock(
            side_effect=OperationalError('broker is down'))

        r = self.post('/api/task/send-task/foo', body={})

        self.assertEqual(503, r.code)


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


class MockTasks:

    @staticmethod
    def get_task_by_id(events, task_id):
        from celery.events.state import Task
        return Task()


class TaskTests(BaseApiTestCase):
    def setUp(self):
        self.app = super().get_app()
        super().setUp()

    def get_app(self, capp=None):
        return self.app

    @patch('flower.api.tasks.tasks', new=MockTasks)
    def test_task_info(self):
        self.get('/api/task/info/123')

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

    def test_invalid_sort_by(self):
        r = self.get('/api/tasks?sort_by=bogus')

        self.assertEqual(400, r.code)
        self.assertIn('Invalid sort_by', r.body.decode('utf-8'))

    def test_valid_sort_by_descending(self):
        r = self.get('/api/tasks?sort_by=-received')

        self.assertEqual(200, r.code)

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
        self.app.events.state = state

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
