from tests import AsyncHTTPTestCase


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

    def test_logout(self):
        r = self.get('/logout')
        self.assertEqual(200, r.code)
