from tests.unit import AsyncHTTPTestCase


class ErrorTests(AsyncHTTPTestCase):
    def test_404(self):
        r = self.get('/unknown')
        self.assertEqual(404, r.code)
