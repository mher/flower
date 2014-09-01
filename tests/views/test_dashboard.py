from tests import AsyncHTTPTestCase


class DashboardTests(AsyncHTTPTestCase):
    def test_workers_page(self):
        r = self.get('/dashboard')
        self.assertEqual(200, r.code)
        self.assertTrue('Broker' in str(r.body))

    def test_unknown_worker(self):
        r = self.get('/worker/unknown')
        self.assertEqual(404, r.code)
        self.assertTrue('Unknown worker' in str(r.body))
