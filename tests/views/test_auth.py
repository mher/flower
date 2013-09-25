import base64
from tests import AsyncHTTPTestCase


class AuthTests(AsyncHTTPTestCase):
    def get_app(self, celery_app=None, events=None, state=None):
        super(AuthTests, self).get_app(celery_app, events, state)
        self.app.basic_auth = "hello:world"
        return self.app

    def test_auth_without_credentials(self):
        r = self.get('/')
        self.assertEqual(401, r.code)

    def test_auth_with_bad_credentials(self):
        credentials = base64.b64encode("not:good".encode()).decode()
        r = self.get('/', headers={"Authorization": "Basic " + credentials})
        self.assertEqual(401, r.code)

    def test_auth_with_good_credentials(self):
        credentials = base64.b64encode("hello:world".encode()).decode()
        r = self.get('/', headers={"Authorization": "Basic " + credentials})
        self.assertEqual(200, r.code)
