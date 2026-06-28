import json
from unittest.mock import AsyncMock, MagicMock, patch

from flower.views.auth import authenticate, validate_auth_option
from tests.unit import AsyncHTTPTestCase


class BasicAuthTests(AsyncHTTPTestCase):
    def test_with_single_creds(self):
        with self.mock_option('basic_auth', ['foo:bar']):
            r = self.fetch('/')
            self.assertEqual(401, r.code)
            r = self.fetch('/', auth_username='foo', auth_password='bar')
            self.assertEqual(200, r.code)
            r = self.fetch('/', auth_username='foo', auth_password='bar2')
            self.assertEqual(401, r.code)

    def test_with_multiple_creds(self):
        with self.mock_option('basic_auth', ['user1:pswd1', 'user2:pswd2']):
            r = self.fetch('/')
            self.assertEqual(401, r.code)
            r = self.fetch('/', auth_username='user1', auth_password='pswd1')
            self.assertEqual(200, r.code)
            r = self.fetch('/', auth_username='user2', auth_password='pswd2')
            self.assertEqual(200, r.code)
            r = self.fetch('/', auth_username='user1', auth_password='pswd2')
            self.assertEqual(401, r.code)


class AuthTests(AsyncHTTPTestCase):
    def test_validate_auth_option(self):
        self.assertTrue(validate_auth_option("mail@example.com"))
        self.assertTrue(validate_auth_option(".*@example.com"))
        self.assertTrue(validate_auth_option("one.*@example.com"))
        self.assertTrue(validate_auth_option("one.*two@example.com"))
        self.assertFalse(validate_auth_option(".*@.*example.com"))
        self.assertFalse(validate_auth_option("one@domain1.com|.*@domain2.com"))
        self.assertTrue(validate_auth_option("one@example.com|two@example.com"))
        self.assertFalse(validate_auth_option("mail@.*example.com"))
        self.assertFalse(validate_auth_option(".*example.com"))

    def test_authenticate_single_email(self):
        self.assertTrue(authenticate("mail@example.com", "mail@example.com"))
        self.assertFalse(authenticate("mail@example.com", "foo@example.com"))
        self.assertFalse(authenticate("mail@example.com", "long.mail@example.com"))
        self.assertFalse(authenticate("mail@example.com", ""))
        self.assertFalse(authenticate("me@gmail.com", "me@gmail.com.attacker.com"))
        self.assertFalse(authenticate("me@gmail.com", "*"))

    def test_authenticate_email_list(self):
        self.assertTrue(authenticate("one@example.com|two@example.net", "one@example.com"))
        self.assertTrue(authenticate("one@example.com|two@example.net", "two@example.net"))
        self.assertFalse(authenticate("one@example.com|two@example.net", "two@example.com"))
        self.assertFalse(authenticate("one@example.com|two@example.net", "one@example.net"))
        self.assertFalse(authenticate("one@example.com|two@example.net", "mail@gmail.com"))
        self.assertFalse(authenticate("one@example.com|two@example.net", ""))
        self.assertFalse(authenticate("one@example.com|two@example.net", "*"))

    def test_authenticate_wildcard_email(self):
        self.assertTrue(authenticate(".*@example.com", "one@example.com"))
        self.assertTrue(authenticate("one.*@example.com", "one@example.com"))
        self.assertTrue(authenticate("one.*@example.com", "one.two@example.com"))
        self.assertFalse(authenticate(".*@example.com", "attacker@example.com.attacker.com"))
        self.assertFalse(authenticate(".*@corp.example.com", "attacker@corpZexample.com"))
        self.assertFalse(authenticate(".*@corp\\.example\\.com", "attacker@corpZexample.com"))


_OAUTH_SETTINGS = {
    'key': 'test-client-id',
    'secret': 'test-client-secret',
    'redirect_uri': 'http://localhost:5555/login',
}


class GithubLoginHandlerDeviceFlowTests(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        self._app.settings['oauth'] = _OAUTH_SETTINGS

    def test_post_returns_device_code_json(self):
        client = MagicMock()
        client.fetch = AsyncMock(return_value=MagicMock(
            error=None,
            body=json.dumps({'user_code': 'ABCD-1234'}).encode(),
        ))
        with self.mock_option('auth_provider', 'flower.views.auth.GithubLoginHandler'), \
             self.mock_option('auth', '.*@example.com'), \
             patch('flower.views.auth.GithubLoginHandler.get_auth_http_client', return_value=client):
            r = self.fetch('/login', method='POST', body='')
            self.assertEqual(200, r.code)
            self.assertEqual('ABCD-1234', json.loads(r.body)['user_code'])

    def test_get_authorization_pending_returns_202(self):
        client = MagicMock()
        client.fetch = AsyncMock(return_value=MagicMock(
            error=None,
            body=json.dumps({'error': 'authorization_pending'}).encode(),
        ))
        with self.mock_option('auth_provider', 'flower.views.auth.GithubLoginHandler'), \
             self.mock_option('auth', '.*@example.com'), \
             patch('flower.views.auth.GithubLoginHandler.get_auth_http_client', return_value=client):
            r = self.fetch('/login?device_code=dev123')
            self.assertEqual(202, r.code)

    def test_get_device_auth_error_returns_403(self):
        client = MagicMock()
        client.fetch = AsyncMock(return_value=MagicMock(
            error=None,
            body=json.dumps({'error': 'expired_token'}).encode(),
        ))
        with self.mock_option('auth_provider', 'flower.views.auth.GithubLoginHandler'), \
             self.mock_option('auth', '.*@example.com'), \
             patch('flower.views.auth.GithubLoginHandler.get_auth_http_client', return_value=client):
            r = self.fetch('/login?device_code=dev123')
            self.assertEqual(403, r.code)

    def test_get_successful_auth_sets_cookie_and_redirects(self):
        client = MagicMock()
        client.fetch = AsyncMock(side_effect=[
            MagicMock(error=None, body=json.dumps({'access_token': 'tok123'}).encode()),
            MagicMock(error=None, body=json.dumps(
                [{'email': 'user@example.com', 'verified': True}]).encode()),
        ])
        with self.mock_option('auth_provider', 'flower.views.auth.GithubLoginHandler'), \
             self.mock_option('auth', '.*@example.com'), \
             patch('flower.views.auth.GithubLoginHandler.get_auth_http_client', return_value=client):
            r = self.fetch('/login?device_code=dev123', follow_redirects=False)
            self.assertEqual(302, r.code)
            self.assertIn('user', r.headers.get('Set-Cookie', ''))
