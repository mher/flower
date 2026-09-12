from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

import tornado.auth
from tornado.web import create_signed_value

from flower.urls import settings
from flower.utils.authentication import authenticate, validate_auth_option
from flower.views import BaseHandler
from flower.views.auth import (GithubLoginHandler, OAuth2StateMixin,
                               get_next_url, is_safe_redirect)
from tests.unit import AsyncHTTPTestCase


class DummyLoginHandler(BaseHandler):
    def get(self):
        self.write('login page')


class GithubEmailApiUrlTests(TestCase):
    def test_github_com_uses_api_subdomain(self):
        with patch.object(GithubLoginHandler, '_OAUTH_DOMAIN', 'github.com'):
            self.assertEqual('https://api.github.com/user/emails',
                             GithubLoginHandler._email_api_url())

    def test_enterprise_server_uses_api_v3_path(self):
        with patch.object(GithubLoginHandler, '_OAUTH_DOMAIN',
                          'ghe.example.com'):
            self.assertEqual('https://ghe.example.com/api/v3/user/emails',
                             GithubLoginHandler._email_api_url())


class LoginRouteTests(AsyncHTTPTestCase):
    def test_login_trailing_slash(self):
        provider = f'{DummyLoginHandler.__module__}.DummyLoginHandler'
        with self.mock_option('auth_provider', provider):
            r = self.fetch('/login')
            self.assertEqual(200, r.code)
            r = self.fetch('/login/')
            self.assertEqual(200, r.code)


class LogoutTests(AsyncHTTPTestCase):
    @staticmethod
    def session_cookie(email='user@example.com'):
        signed = create_signed_value(settings['cookie_secret'], 'user', email)
        return {'Cookie': 'user=' + signed.decode()}

    def test_logout_clears_the_session_cookie(self):
        with self.mock_option('auth', '.*@example.com'):
            r = self.fetch('/logout', headers=self.session_cookie())
            self.assertEqual(200, r.code)
            cleared = [c for c in r.headers.get_list('Set-Cookie') if c.startswith('user=')]
            self.assertEqual(1, len(cleared))
            self.assertIn('expires=', cleared[0].lower())
            body = r.body.decode('utf-8')
            self.assertIn('You have been logged out', body)
            self.assertIn('app-navbar', body)
            self.assertNotIn('/logout"', body)

    def test_logout_page_needs_no_session(self):
        with self.mock_option('auth', '.*@example.com'):
            r = self.fetch('/logout', follow_redirects=False)
            self.assertEqual(200, r.code)

    def test_navbar_shows_logout_for_oauth_sessions(self):
        with self.mock_option('auth', '.*@example.com'):
            r = self.fetch('/', headers=self.session_cookie())
            self.assertEqual(200, r.code)
            body = r.body.decode('utf-8')
            self.assertIn('href="/logout"', body)
            self.assertIn('Log out user@example.com', body)

    def test_navbar_hides_logout_without_oauth(self):
        r = self.fetch('/')
        self.assertEqual(200, r.code)
        self.assertNotIn('/logout', r.body.decode('utf-8'))

    def test_navbar_hides_logout_for_basic_auth(self):
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.fetch('/', auth_username='user', auth_password='pass')
            self.assertEqual(200, r.code)
            self.assertNotIn('/logout', r.body.decode('utf-8'))


class _StateHandler(OAuth2StateMixin):
    def __init__(self, cookie=None, state_arg=None):
        self._cookies = {'oauth_state': cookie.encode()} if cookie else {}
        self._state_arg = state_arg

    def set_secure_cookie(self, name, value):
        self._cookies[name] = value.encode()

    def get_secure_cookie(self, name):
        return self._cookies.get(name)

    def clear_cookie(self, name):
        self._cookies.pop(name, None)

    def get_argument(self, name, default=None):
        return self._state_arg if self._state_arg is not None else default


def _handler(next_value, url_prefix=''):
    options = SimpleNamespace(url_prefix=url_prefix)
    return SimpleNamespace(
        application=SimpleNamespace(options=options),
        get_argument=lambda name, default: (
            default if next_value is None else next_value),
    )


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


class AuthTests(TestCase):
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

    def test_is_safe_redirect(self):
        self.assertTrue(is_safe_redirect('/'))
        self.assertTrue(is_safe_redirect('/workers'))
        self.assertTrue(is_safe_redirect('/tasks?state=SUCCESS'))
        self.assertFalse(is_safe_redirect(''))
        self.assertFalse(is_safe_redirect('workers'))
        self.assertFalse(is_safe_redirect('//evil.com'))
        self.assertFalse(is_safe_redirect('/\\evil.com'))
        self.assertFalse(is_safe_redirect('https://evil.com'))
        self.assertFalse(is_safe_redirect('http:evil.com'))

    def test_get_next_url_rejects_open_redirects(self):
        self.assertEqual('/', get_next_url(_handler('//evil.com')))
        self.assertEqual('/', get_next_url(_handler('https://evil.com')))
        self.assertEqual('/flower', get_next_url(_handler('//evil.com', 'flower')))

    def test_get_next_url_allows_local_paths(self):
        self.assertEqual('/tasks', get_next_url(_handler('/tasks')))
        self.assertEqual('/', get_next_url(_handler(None)))
        self.assertEqual('/flower', get_next_url(_handler(None, 'flower')))
        # a bare path is normalized under the prefix, matching prior behavior
        self.assertEqual('/workers', get_next_url(_handler('workers', 'flower')))

    def test_oauth_state_roundtrip(self):
        h = _StateHandler()
        state = h.set_oauth_state()
        self.assertEqual(state, h.get_secure_cookie('oauth_state').decode())

    def test_verify_oauth_state_matches_and_clears(self):
        h = _StateHandler(cookie='abc', state_arg='abc')
        h.verify_oauth_state()
        self.assertIsNone(h.get_secure_cookie('oauth_state'))

    def test_verify_oauth_state_mismatch(self):
        h = _StateHandler(cookie='abc', state_arg='xyz')
        self.assertRaises(tornado.auth.AuthError, h.verify_oauth_state)

    def test_verify_oauth_state_missing_cookie(self):
        h = _StateHandler(cookie=None, state_arg='abc')
        self.assertRaises(tornado.auth.AuthError, h.verify_oauth_state)

    def test_authenticate_wildcard_email(self):
        self.assertTrue(authenticate(".*@example.com", "one@example.com"))
        self.assertTrue(authenticate("one.*@example.com", "one@example.com"))
        self.assertTrue(authenticate("one.*@example.com", "one.two@example.com"))
        self.assertFalse(authenticate(".*@example.com", "attacker@example.com.attacker.com"))
        self.assertFalse(authenticate(".*@corp.example.com", "attacker@corpZexample.com"))
        self.assertFalse(authenticate(r".*@corp\.example\.com", "attacker@corpZexample.com"))
