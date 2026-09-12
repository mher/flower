from unittest.mock import patch

import tornado.auth

from flower.views import BaseHandler
from tests.unit import AsyncHTTPTestCase


class FailingLoginHandler(BaseHandler):
    def get(self):
        raise tornado.auth.AuthError('State tokens do not match')


class ErrorTests(AsyncHTTPTestCase):
    def test_auth_error_renders_friendly_page(self):
        provider = f'{FailingLoginHandler.__module__}.FailingLoginHandler'
        with (
            self.mock_option('auth_provider', provider),
            patch('tornado.web.app_log.error') as log_error,
            self.assertLogs('flower.views', level='WARNING'),
        ):
            r = self.fetch('/login')

        self.assertEqual(403, r.code)
        self.assertIn('try logging in again', str(r.body))
        self.assertNotIn('Traceback', str(r.body))
        log_error.assert_not_called()

    def test_404(self):
        r = self.get('/unknown')
        self.assertEqual(404, r.code)

    def test_404_without_basic_auth_credentials(self):
        with (
            self.mock_option('basic_auth', ['user:pass']),
            patch('tornado.web.app_log.error') as log_error,
        ):
            response = self.get('/unknown')

        self.assertEqual(404, response.code)
        log_error.assert_not_called()
