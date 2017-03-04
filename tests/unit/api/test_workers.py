import json

import mock

from flower.api.control import ControlHandler

from tests.unit import AsyncHTTPTestCase


inspect_response = {
    'celery@worker1':  [
        "tasks.add",
        "tasks.sleep"
    ],
}

empty_inspect_response = {
    'celery@worker1': []
}


@mock.patch.object(ControlHandler, 'INSPECT_METHODS',
                   new_callable=mock.PropertyMock,
                   return_value=['inspect_method'])
class ListWorkersTest(AsyncHTTPTestCase):

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
            ControlHandler.worker_cache['celery@worker1']['inspect_method']
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
            ControlHandler.worker_cache['celery@worker1']['inspect_method']
        )
