import os
from unittest.mock import patch

from tests.unit import AsyncHTTPTestCase


class SecurityHeaderTests(AsyncHTTPTestCase):
    def test_nosniff_on_page(self):
        r = self.get('/')
        self.assertEqual('nosniff', r.headers.get('X-Content-Type-Options'))

    def test_nosniff_on_api_error(self):
        # send_error clears the headers, so it has to be re-applied there
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          auth_username='user', auth_password='pass')
            self.assertEqual(404, r.code)
            self.assertEqual('nosniff', r.headers.get('X-Content-Type-Options'))


class CorsHeaderTests(AsyncHTTPTestCase):
    DATATABLE = ('/tasks/datatable?draw=1&start=0&length=10&search[value]='
                 '&order[0][column]=0&order[0][dir]=asc&columns[0][data]=name')

    def test_no_cors_by_default(self):
        for url in ('/', self.DATATABLE, '/workers?json=1'):
            r = self.get(url)
            self.assertEqual(200, r.code)
            self.assertNotIn('Access-Control-Allow-Origin', r.headers)

    @patch.dict(os.environ, {'FLOWER_UNAUTHENTICATED_API': 'true'})
    def test_cors_when_unauthenticated_api_enabled(self):
        r = self.get(self.DATATABLE)
        self.assertEqual(200, r.code)
        self.assertEqual('*', r.headers.get('Access-Control-Allow-Origin'))

    @patch.dict(os.environ, {'FLOWER_UNAUTHENTICATED_API': 'true'})
    def test_no_cors_with_authentication(self):
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.get('/', auth_username='user', auth_password='pass')
            self.assertEqual(200, r.code)
            self.assertNotIn('Access-Control-Allow-Origin', r.headers)
