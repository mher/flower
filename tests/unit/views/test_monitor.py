import re
import time
from datetime import datetime, timedelta

from celery.events import Event
from flower.events import EventsState
from tests.unit.utils import task_succeeded_events
from tests.unit import AsyncHTTPTestCase


class PrometheusTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(PrometheusTests, self).get_app()
        super(PrometheusTests, self).setUp()

    def get_app(self):
        return self.app

    def test_metrics(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = [Event('worker-online', hostname=worker_name), Event('worker-heartbeat', hostname=worker_name, active=1)]
        events += task_succeeded_events(worker=worker_name, name=task_name, id='123')

        task_received = time.time()
        task_started = task_received + 3
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            if e['type'] == 'task-received':
                e['timestamp'] = task_received
            if e['type'] == 'task-started':
                e['timestamp'] = task_started
            state.event(e)
        self.app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')
        events = dict(re.findall('flower_events_total{task="task1",type="(task-.*)",worker="worker1"} (.*)', metrics))

        self.assertTrue('task-received' in events)
        self.assertTrue('task-started' in events)
        self.assertTrue('task-succeeded' in events)
        self.assertTrue(
            f'flower_task_queuing_time_at_worker_seconds{{task="{task_name}",worker="{worker_name}"}} 3.0' in metrics
        )

        self.assertTrue(f'flower_worker_online{{worker="{worker_name}"}} 1.0' in metrics)
        self.assertTrue(f'flower_worker_number_of_currently_executing_tasks{{worker="{worker_name}"}} 1.0' in metrics)

    def test_does_not_compute_queuing_time_if_task_has_eta(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = [Event('worker-online', hostname=worker_name)]
        events += task_succeeded_events(
            worker=worker_name, name=task_name, id='123', eta=datetime.now() + timedelta(hours=4)
        )
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertFalse(f'flower_task_queuing_time_at_worker_seconds{{task="{task_name}",worker="{worker_name}"}} ' in metrics)

    def test_worker_online_metric_worker_is_offline(self):
        state = EventsState()
        worker_name = 'worker1'
        state.get_or_create_worker(worker_name)
        events = [Event('worker-offline', hostname=worker_name)]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self.app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(f'flower_worker_online{{worker="{worker_name}"}} 0.0' in metrics)


class HealthcheckTests(AsyncHTTPTestCase):
    def setUp(self):
        self.app = super(HealthcheckTests, self).get_app()
        super(HealthcheckTests, self).setUp()

    def get_app(self):
        return self.app

    def test_healthcheck_route(self):
        response = self.get('/healthcheck').body.decode('utf-8')
        self.assertEquals(response, 'OK')
