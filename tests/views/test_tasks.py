from tests import AsyncHTTPTestCase


class TaskTest(AsyncHTTPTestCase):
    def test_task_page(self):
        r = self.get('/tasks')
        self.assertEqual(200, r.code)
        self.assertTrue('Seen task types' in str(r.body))

    def test_unknown_task(self):
        r = self.get('/task/unknown')
        self.assertEqual(404, r.code)
        self.assertTrue('Unknown task' in str(r.body))
