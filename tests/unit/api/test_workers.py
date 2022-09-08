import json
from unittest import mock

from flower.inspector import Inspector

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

inspect_response_with_non_serializable_args = {
    'celery@worker1' : {
        'active': {
            'id': '1234',
            'args': [set([1,2])]
        }
    }
}


@mock.patch.object(Inspector, 'methods',
                   new_callable=mock.PropertyMock,
                   return_value=['inspect_method'])
class ListWorkersTest(AsyncHTTPTestCase):

    def test_non_serialisable_args_in_response(self, m_inspect):
        celery = self._app.capp
        celery.control.inspect = mock.Mock()
        celery.control.inspect.return_value.inspect_method = mock.Mock(
            return_value=inspect_response_with_non_serializable_args
        )
        # this will fail with a response code of 500
        self.get('/api/workers?refresh=1')

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
