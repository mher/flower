from unittest.mock import patch

from tests.unit import AsyncHTTPTestCase


class ErrorTests(AsyncHTTPTestCase):
    def test_404(self):
        r = self.get('/unknown')
        self.assertEqual(404, r.code)

    def test_404_without_basic_auth_credentials(self):
        with self.mock_option('basic_auth', ['user:pass']):
            with patch('tornado.web.app_log.error') as log_error:
                response = self.get('/unknown')

        self.assertEqual(404, response.code)
        log_error.assert_not_called()
