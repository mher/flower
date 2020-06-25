import re
import time

from celery.events import Event
from flower.events import EventsState
from tests.unit.utils import task_succeeded_events
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


class PrometheusTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(PrometheusTests, self).get_app()
        super(PrometheusTests, self).setUp()

    def get_app(self):
        return self.app

    def test_metrics(self):
        state = EventsState()
        state.get_or_create_worker('worker1')
        events = [Event('worker-online', hostname='worker1')]
        events += task_succeeded_events(worker='worker1', name='task1', id='123')
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')
        events = dict(re.findall('flower_events_total{task="task1",type="(task-.*)",worker="worker1"} (.*)', metrics))

        self.assertTrue('task-received' in events)
        self.assertTrue('task-started' in events)
        self.assertTrue('task-succeeded' in events)
