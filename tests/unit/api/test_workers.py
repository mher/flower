import json
from unittest import mock

from flower.inspector import Inspector

from . import BaseApiTestCase

inspect_response = {
    'celery@worker1':  [
        "tasks.add",
        "tasks.sleep"
    ],
}

empty_inspect_response = {
    'celery@worker1': []
}


@mock.patch.object(Inspector, 'inspect_methods',
                   new_callable=mock.PropertyMock,
                   return_value=['inspect_method'])
class ListWorkersTest(BaseApiTestCase):

    def test_refresh_cache(self, m_inspect):
        celery = self._app.capp
        celery.control.inspect = mock.Mock()
        celery.control.inspect.return_value.inspect_method = mock.Mock(
            return_value=inspect_response
        )

        r = self.get('/api/workers?refresh=1')
        celery.control.inspect.assert_called_once_with(
            timeout=1,
            destination=None
        )

        body = json.loads(r.body.decode("utf-8"))
        self.assertEqual(
            inspect_response['celery@worker1'],
            body['celery@worker1']['inspect_method']
        )
        self.assertIn('timestamp', body['celery@worker1'])
        self.assertEqual(
            inspect_response['celery@worker1'],
            self._app.workers['celery@worker1']['inspect_method']
        )

    def test_refresh_cache_with_empty_response(self, m_inspect):
        celery = self._app.capp
        celery.control.inspect = mock.Mock()
        celery.control.inspect.return_value.inspect_method = mock.Mock(
            return_value=inspect_response
        )
        r = self.get('/api/workers?refresh=1')

        celery.control.inspect.return_value.inspect_method = mock.Mock(
            return_value=empty_inspect_response
        )

        r = self.get('/api/workers?refresh=1')

        body = json.loads(r.body.decode("utf-8"))
        self.assertEqual(
            [],
            body['celery@worker1']['inspect_method']
        )
        self.assertIn('timestamp', body['celery@worker1'])
        self.assertEqual(
            [],
            self._app.workers['celery@worker1']['inspect_method']
        )


class MaskedWorkerSettingsTest(BaseApiTestCase):
    def get_app(self, capp=None):
        with self.mock_option('masked_worker_settings', ['sentry_dsn']):
            return super().get_app(capp)

    def test_masks_settings(self):
        self._app.inspector._on_update('worker1', 'conf', {
            'SENTRY_DSN': 'https://secret@sentry.example.com/1', 'worker_concurrency': 4})

        r = self.get('/api/workers?workername=worker1')

        body = json.loads(r.body.decode('utf-8'))
        self.assertEqual({'SENTRY_DSN': '********', 'worker_concurrency': 4}, body['worker1']['conf'])
