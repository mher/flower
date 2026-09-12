import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
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
        tomorrow = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
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
