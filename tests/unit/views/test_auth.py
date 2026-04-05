import importlib
import os
from flower.views.auth import authenticate, validate_auth_option, GithubLoginHandler, GitLabLoginHandler
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
        self.assertFalse(authenticate(".*@corp\.example\.com", "attacker@corpZexample.com"))


class OAuthTests(AsyncHTTPTestCase):
    def test_github_oauth_urls_default(self):
        # Test default GitHub.com URLs
        self.assertEqual(GithubLoginHandler._OAUTH_DOMAIN, 'github.com')
        self.assertEqual(GithubLoginHandler._OAUTH_API_URL, 'https://api.github.com/user/emails')
        self.assertEqual(GithubLoginHandler._OAUTH_AUTHORIZE_URL, 'https://github.com/login/oauth/authorize')
        self.assertEqual(GithubLoginHandler._OAUTH_ACCESS_TOKEN_URL, 'https://github.com/login/oauth/access_token')

    def test_github_oauth_urls_enterprise(self):
        # Test GitHub Enterprise URLs by reloading the module with env set
        import flower.views.auth as auth_module
        original_env = os.environ.get('FLOWER_GITHUB_OAUTH_DOMAIN')
        try:
            os.environ['FLOWER_GITHUB_OAUTH_DOMAIN'] = 'github.example.com'
            importlib.reload(auth_module)
            self.assertEqual(auth_module.GithubLoginHandler._OAUTH_DOMAIN, 'github.example.com')
            self.assertEqual(auth_module.GithubLoginHandler._OAUTH_API_URL, 'https://github.example.com/api/v3/user/emails')
            self.assertEqual(auth_module.GithubLoginHandler._OAUTH_AUTHORIZE_URL, 'https://github.example.com/oauth/authorize')
            self.assertEqual(auth_module.GithubLoginHandler._OAUTH_ACCESS_TOKEN_URL, 'https://github.example.com/oauth/access_token')
        finally:
            if original_env is None:
                os.environ.pop('FLOWER_GITHUB_OAUTH_DOMAIN', None)
            else:
                os.environ['FLOWER_GITHUB_OAUTH_DOMAIN'] = original_env
            importlib.reload(auth_module)  # reset to default

    def test_gitlab_oauth_urls_default(self):
        # Test default GitLab.com URLs
        self.assertEqual(GitLabLoginHandler._OAUTH_GITLAB_DOMAIN, 'gitlab.com')
        self.assertEqual(GitLabLoginHandler._OAUTH_AUTHORIZE_URL, 'https://gitlab.com/oauth/authorize')
        self.assertEqual(GitLabLoginHandler._OAUTH_ACCESS_TOKEN_URL, 'https://gitlab.com/oauth/token')
