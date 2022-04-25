from tests.unit import AsyncHTTPTestCase

class ApiTestCase(AsyncHTTPTestCase):
    def get(self, url, **kwargs):
        with self.mock_option('dangerous_allow_unauth_api', True):
            return super().get(url, **kwargs)

    def post(self, url, **kwargs):
        with self.mock_option('dangerous_allow_unauth_api', True):
            return super().post(url, **kwargs)
