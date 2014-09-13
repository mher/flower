import base64
from tests import AsyncHTTPTestCase


class AuthTests(AsyncHTTPTestCase):
    def test_auth_without_credentials(self):
        ba = self._app.options.basic_auth
        self._app.options.basic_auth = ["hello:world"]
        r = self.get('/')
        self._app.options.basic_auth = ba
        self.assertEqual(401, r.code)

    def test_auth_with_bad_credentials(self):
        ba = self._app.options.basic_auth
        self._app.options.basic_auth = ["hello:world"]
        credentials = base64.b64encode("not:good".encode()).decode()
        r = self.get('/', headers={"Authorization": "Basic " + credentials})
        self._app.options.basic_auth = ba
        self.assertEqual(401, r.code)

    def test_auth_with_good_credentials(self):
        ba = self._app.options.basic_auth
        self._app.options.basic_auth = ["hello:world"]
        credentials = base64.b64encode("hello:world".encode()).decode()
        r = self.get('/', headers={"Authorization": "Basic " + credentials})
        self._app.options.basic_auth = ba
        self.assertEqual(200, r.code)
