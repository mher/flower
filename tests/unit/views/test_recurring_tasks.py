from tests.unit import AsyncHTTPTestCase


class TestRecurringTasksView(AsyncHTTPTestCase):
    def test_recurring_tasks_page_empty(self):
        res = self.get('/recurring-tasks')
        self.assertEqual(200, res.code)
        self.assertIn(b'Recurring tasks', res.body)
        self.assertIn(b'recurring-tasks-table', res.body)

    def test_recurring_tasks_page_with_entries(self):
        self._app.capp.conf.beat_schedule = {
            'check-feed': {
                'task': 'app.tasks.check_feed',
                'schedule': 30.0,
            }
        }
        res = self.get('/recurring-tasks')
        self.assertEqual(200, res.code)
        self.assertIn(b'check-feed', res.body)
        self.assertIn(b'app.tasks.check_feed', res.body)
        self.assertIn(b'every 30s', res.body)

    def test_recurring_task_detail_page(self):
        self._app.capp.conf.beat_schedule = {
            'check-feed': {
                'task': 'app.tasks.check_feed',
                'schedule': 30.0,
                'args': [1, 2],
                'kwargs': {'interval': 10},
                'options': {'queue': 'feed'},
            }
        }
        res = self.get('/recurring-task/check-feed')
        self.assertEqual(200, res.code)
        self.assertIn(b'Recurring task details', res.body)
        self.assertIn(b'check-feed', res.body)
        self.assertIn(b'app.tasks.check_feed', res.body)
        self.assertIn(b'every 30s', res.body)
        self.assertIn(b'View task history', res.body)

    def test_recurring_task_detail_page_not_found(self):
        self._app.capp.conf.beat_schedule = {}
        res = self.get('/recurring-task/non-existent-task')
        self.assertEqual(404, res.code)
