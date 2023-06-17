from tests.unit import AsyncHTTPTestCase


class TestBrokerView(AsyncHTTPTestCase):
    def test_empty_page(self):
        res = self.get('/broker')
        self.assertEqual(200, res.code)
