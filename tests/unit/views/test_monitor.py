import time

from tests.unit import AsyncHTTPTestCase


class MonitorTest(AsyncHTTPTestCase):
    def test_monitor_page(self):
        r = self.get('/monitor')
        self.assertEqual(200, r.code)
        self.assertTrue('Succeeded tasks' in str(r.body))
        self.assertTrue('Failed tasks' in str(r.body))

    def test_monitor_succeeded_tasks(self):
        r = self.get('/monitor/succeeded-tasks?lastquery=%s' % time.time())
        self.assertEqual(200, r.code)

    def test_monitor_completion_time(self):
        r = self.get('/monitor/completion-time?lastquery=%s' % time.time())
        self.assertEqual(200, r.code)

    def test_monitor_failed_tasks(self):
        r = self.get('/monitor/failed-tasks?lastquery=%s' % time.time())
        self.assertEqual(200, r.code)
