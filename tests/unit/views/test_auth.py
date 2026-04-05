from flower.views.auth import authenticate, validate_auth_option, GithubLoginHandler
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
        self.assertFalse(authenticate(r".*@corp\.example\.com", "attacker@corpZexample.com"))


class OAuthTests(AsyncHTTPTestCase):
    def test_get_oauth_urls_for_github_com(self):
        api_url, authorize_url, access_token_url = GithubLoginHandler._get_oauth_urls('github.com')
        self.assertEqual(api_url, 'https://api.github.com/user/emails')
        self.assertEqual(authorize_url, 'https://github.com/login/oauth/authorize')
        self.assertEqual(access_token_url, 'https://github.com/login/oauth/access_token')

    def test_get_oauth_urls_for_github_enterprise(self):
        api_url, authorize_url, access_token_url = GithubLoginHandler._get_oauth_urls('github.example.com')
        self.assertEqual(api_url, 'https://github.example.com/api/v3/user/emails')
        self.assertEqual(authorize_url, 'https://github.example.com/oauth/authorize')
        self.assertEqual(access_token_url, 'https://github.example.com/oauth/access_token')

    def test_github_login_handler_defaults_remain_github(self):
        self.assertEqual(GithubLoginHandler._OAUTH_DOMAIN, 'github.com')
        self.assertEqual(GithubLoginHandler._OAUTH_API_URL, 'https://api.github.com/user/emails')
        self.assertEqual(GithubLoginHandler._OAUTH_AUTHORIZE_URL, 'https://github.com/login/oauth/authorize')
        self.assertEqual(GithubLoginHandler._OAUTH_ACCESS_TOKEN_URL, 'https://github.com/login/oauth/access_token')
