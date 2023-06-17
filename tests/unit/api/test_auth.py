from tests.unit import AsyncHTTPTestCase


class BasicAuthTests(AsyncHTTPTestCase):
    def test_auth(self):
        with self.mock_option('basic_auth', ['user1:pswd1', 'user2:pswd2']):
            r = self.fetch('/api/workers')
            self.assertEqual(401, r.code)
            r = self.fetch('/api/workers', auth_username='user1', auth_password='pswd1')
            self.assertEqual(200, r.code)
            r = self.fetch('/api/workers', auth_username='user2', auth_password='pswd2')
            self.assertEqual(200, r.code)
            r = self.fetch('/api/workers', auth_username='user1', auth_password='pswd2')
            self.assertEqual(401, r.code)
