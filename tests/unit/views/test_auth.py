from tests.unit import AsyncHTTPTestCase
from unittest.mock import patch

from tornado.options import options

from flower.command import extract_settings
from flower.views import RequireAuthMixin

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

class OauthTests(AsyncHTTPTestCase):
    def test_unauth_api_flag(self):
        r = self.fetch('/api/tasks')
        self.assertEqual(401, r.code)

        with self.mock_option('dangerous_allow_unauth_api', True):
            r = self.fetch('/api/tasks')
            self.assertEqual(200, r.code)

    def test_valid_email_list(self):
        auth_mixin = RequireAuthMixin()
        with patch.object(auth_mixin, 'settings', {'auth_email_list': ['a@example.com']}, create=True):
            self.assertTrue(auth_mixin.is_valid_email('a@example.com'))
            self.assertFalse(auth_mixin.is_valid_email('b@example.com'))
            self.assertFalse(auth_mixin.is_valid_email('a@example.com.attacker.com'))
            self.assertFalse(auth_mixin.is_valid_email('a@exampleZcom'))
            self.assertFalse(auth_mixin.is_valid_email('aaa@example.com'))

    def test_valid_email_regex_simple(self):
        opts = options.mockable()
        with (patch.dict('flower.urls.settings') as settings, patch.object(opts, 'auth', '.*@example.com')):
            extract_settings()

            auth_mixin = RequireAuthMixin()
            with patch.object(auth_mixin, 'settings', {'auth_regex': settings['auth_regex']}, create=True):
                self.assertTrue(auth_mixin.is_valid_email('a@example.com'))
                self.assertTrue(auth_mixin.is_valid_email('b@example.com'))
                self.assertFalse(auth_mixin.is_valid_email('a@example.com.attacker.com'))
                self.assertFalse(auth_mixin.is_valid_email('a@exampleZcom'))
                self.assertTrue(auth_mixin.is_valid_email('aaa@example.com'))
                self.assertFalse(auth_mixin.is_valid_email('a@example.com@example.com'))
                self.assertFalse(auth_mixin.is_valid_email('"a@example.com"@example.com'))

class AuthConfigTests(AsyncHTTPTestCase):
    def test_auth_email_list(self):
        opts = options.mockable()
        with patch.dict('flower.urls.settings') as settings:
            with patch.object(opts, 'auth', 'user@example.com'):
                extract_settings()
                self.assertEqual(settings['auth_email_list'], ['user@example.com'])

            with patch.object(opts, 'auth', 'user1@example.com|user2@example.com'):
                extract_settings()
                self.assertEqual(settings['auth_email_list'], ['user1@example.com', 'user2@example.com'])

    def test_auth_wildcard(self):
        opts = options.mockable()
        with patch.dict('flower.urls.settings') as settings:
            with patch.object(opts, 'auth', '.*@example.com'):
                extract_settings()
                email_regex = settings['auth_regex'].pattern
                self.assertEqual(email_regex[:2], r'\A')
                self.assertEqual(email_regex[-2:], r'\Z')
                self.assertIn(r'@example\.com\Z', email_regex)

    def test_auth_regex(self):
        opts = options.mockable()
        with patch.dict('flower.urls.settings') as settings:
            with patch.multiple(opts, auth='true', auth_regex='dont_mess_with_this'):
                extract_settings()
                self.assertEqual(settings['auth_regex'].pattern, 'dont_mess_with_this')

    def test_invalid_options(self):
        opts = options.mockable()

        with (patch.dict('flower.urls.settings') as settings,
            patch.object(opts, 'auth', '.*@a.com|somebody@b.com'),
            self.assertRaises(ValueError)):
            extract_settings()

        with (patch.dict('flower.urls.settings') as settings,
            patch.object(opts, 'auth', 'someone@.*'),
            self.assertRaises(ValueError)):
            extract_settings()

        with (patch.dict('flower.urls.settings') as settings,
            patch.object(opts, 'auth', '.*@.*'),
            self.assertRaises(ValueError)):
            extract_settings()
