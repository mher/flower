from mock import MagicMock

from flower.api.control import ControlHandler

from tests.unit import AsyncHTTPTestCase


class UnknownWorkerControlTests(AsyncHTTPTestCase):
    def test_unknown_worker(self):
        r = self.post('/api/worker/shutdown/test', body={})
        self.assertEqual(404, r.code)


class WorkerControlTests(AsyncHTTPTestCase):
    def setUp(self):
        AsyncHTTPTestCase.setUp(self)
        self.is_worker = ControlHandler.is_worker
        ControlHandler.is_worker = lambda *args: True

    def tearDown(self):
        AsyncHTTPTestCase.tearDown(self)
        ControlHandler.is_worker = self.is_worker

    def test_shutdown(self):
        celery = self._app.capp
        celery.control.broadcast = MagicMock()
        r = self.post('/api/worker/shutdown/test', body={})
        self.assertEqual(200, r.code)
        celery.control.broadcast.assert_called_once_with('shutdown',
                                                         destination=['test'])

    def test_pool_restart(self):
        celery = self._app.capp
        celery.control.broadcast = MagicMock(return_value=[{'test': 'ok'}])
        r = self.post('/api/worker/pool/restart/test', body={})
        self.assertEqual(200, r.code)
        celery.control.broadcast.assert_called_once_with(
            'pool_restart',
            arguments={'reload': False},
            destination=['test'],
            reply=True,
        )

    def test_pool_grow(self):
        celery = self._app.capp
        celery.control.pool_grow = MagicMock(return_value=[{'test': 'ok'}])
        r = self.post('/api/worker/pool/grow/test', body={'n': 3})
        self.assertEqual(200, r.code)
        celery.control.pool_grow.assert_called_once_with(
            n=3, reply=True, destination=['test'])

    def test_pool_shrink(self):
        celery = self._app.capp
        celery.control.pool_shrink = MagicMock(return_value=[{'test': 'ok'}])
        r = self.post('/api/worker/pool/shrink/test', body={})
        self.assertEqual(200, r.code)
        celery.control.pool_shrink.assert_called_once_with(
            n=1, reply=True, destination=['test'])

    def test_pool_autoscale(self):
        celery = self._app.capp
        celery.control.broadcast = MagicMock(return_value=[{'test': 'ok'}])
        r = self.post('/api/worker/pool/autoscale/test',
                      body={'min': 2, 'max': 5})
        self.assertEqual(200, r.code)
        celery.control.broadcast.assert_called_once_with(
            'autoscale',
            reply=True, destination=['test'],
            arguments={'min': 2, 'max': 5})

    def test_add_consumer(self):
        celery = self._app.capp
        celery.control.broadcast = MagicMock(
            return_value=[{'test': {'ok': ''}}])
        r = self.post('/api/worker/queue/add-consumer/test',
                      body={'queue': 'foo'})
        self.assertEqual(200, r.code)
        celery.control.broadcast.assert_called_once_with(
            'add_consumer',
            reply=True, destination=['test'],
            arguments={'queue': 'foo'})

    def test_cancel_consumer(self):
        celery = self._app.capp
        celery.control.broadcast = MagicMock(
            return_value=[{'test': {'ok': ''}}])
        r = self.post('/api/worker/queue/cancel-consumer/test',
                      body={'queue': 'foo'})
        self.assertEqual(200, r.code)
        celery.control.broadcast.assert_called_once_with(
            'cancel_consumer',
            reply=True, destination=['test'],
            arguments={'queue': 'foo'})

    def test_task_timeout(self):
        celery = self._app.capp
        celery.control.time_limit = MagicMock(
            return_value=[{'foo': {'ok': ''}}])

        r = self.post(
            '/api/task/timeout/celery.map',
            body={'workername': 'foo', 'hard': 3.1, 'soft': 1.2}
        )
        self.assertEqual(200, r.code)
        celery.control.time_limit.assert_called_once_with(
            'celery.map', hard=3.1, soft=1.2, destination=['foo'],
            reply=True)

    def test_task_ratelimit(self):
        celery = self._app.capp
        celery.control.rate_limit = MagicMock(
            return_value=[{'foo': {'ok': ''}}])

        r = self.post('/api/task/rate-limit/celery.map',
                      body={'workername': 'foo', 'ratelimit': 20})
        self.assertEqual(200, r.code)
        celery.control.rate_limit.assert_called_once_with(
            'celery.map', '20', destination=['foo'], reply=True)

    def test_task_ratelimit_non_integer(self):
        celery = self._app.capp
        celery.control.rate_limit = MagicMock(
            return_value=[{'foo': {'ok': ''}}])

        r = self.post('/api/task/rate-limit/celery.map',
                      body={'workername': 'foo', 'ratelimit': '11/m'})
        self.assertEqual(200, r.code)
        celery.control.rate_limit.assert_called_once_with(
            'celery.map', '11/m', destination=['foo'], reply=True)


class TaskControlTests(AsyncHTTPTestCase):
    def test_revoke(self):
        celery = self._app.capp
        celery.control.revoke = MagicMock()
        r = self.post('/api/task/revoke/test', body={})
        self.assertEqual(200, r.code)
        celery.control.revoke.assert_called_once_with('test',
                                                      terminate=False)

    def test_terminate(self):
        celery = self._app.capp
        celery.control.revoke = MagicMock()
        r = self.post('/api/task/revoke/test', body={'terminate': True})
        self.assertEqual(200, r.code)
        celery.control.revoke.assert_called_once_with('test',
                                                      terminate=True)
