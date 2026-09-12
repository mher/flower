import re
import time
from datetime import datetime, timedelta, timezone

from celery.events import Event
from kombu import uuid

from flower.events import EventsState
from tests.unit import AsyncHTTPTestCase
from tests.unit.utils import task_failed_events, task_succeeded_events


class PrometheusTests(AsyncHTTPTestCase):
    def test_metrics(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = [
            Event('worker-online', hostname=worker_name), Event('worker-heartbeat', hostname=worker_name, active=1)
        ]
        events += task_succeeded_events(worker=worker_name, name=task_name, id='123')

        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')
        events = dict(re.findall('flower_events_total{task="task1",type="(task-.*)",worker="worker1"} (.*)', metrics))

        self.assertTrue('task-received' in events)
        self.assertTrue('task-started' in events)
        self.assertTrue('task-succeeded' in events)

        self.assertTrue(f'flower_worker_online{{worker="{worker_name}"}} 1.0' in metrics)
        self.assertTrue(f'flower_worker_number_of_currently_executing_tasks{{worker="{worker_name}"}} 1.0' in metrics)

    def test_task_runtime_metric_observed_from_events(self):
        state = EventsState()
        worker_name = 'runtime-worker'
        task_name = 'runtime-task'
        state.get_or_create_worker(worker_name)
        events = task_succeeded_events(
            worker=worker_name, name=task_name, id='321', runtime=0.5)
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertIn(
            f'flower_task_runtime_seconds_count{{task="{task_name}",worker="{worker_name}"}} 1.0',
            metrics)
        self.assertIn(
            f'flower_task_runtime_seconds_sum{{task="{task_name}",worker="{worker_name}"}} 0.5',
            metrics)

    def test_task_prefetch_time_metric(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = task_succeeded_events(worker=worker_name, name=task_name, id='123')[:-1]

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
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(
            f'flower_task_prefetch_time_seconds{{task="{task_name}",worker="{worker_name}"}} 3.0' in metrics
        )

    def test_task_prefetch_time_metric_successful_task_resets_metric_to_zero(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = task_succeeded_events(worker=worker_name, name=task_name, id='123')

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
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(
            f'flower_task_prefetch_time_seconds{{task="{task_name}",worker="{worker_name}"}} 0.0' in metrics
        )

    def test_task_prefetch_time_metric_failed_task_resets_metric_to_zero(self):
        state = EventsState()
        worker_name = 'worker1'
        task_name = 'task1'
        state.get_or_create_worker(worker_name)
        events = task_failed_events(worker=worker_name, name=task_name, id='123')

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
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(
            f'flower_task_prefetch_time_seconds{{task="{task_name}",worker="{worker_name}"}} 0.0' in metrics
        )

    def test_task_prefetch_time_metric_does_not_compute_prefetch_time_if_task_has_eta(self):
        state = EventsState()
        worker_name = 'worker2'
        task_name = 'task2'
        state.get_or_create_worker(worker_name)
        events = [Event('worker-online', hostname=worker_name)]
        events += task_succeeded_events(
            worker=worker_name, name=task_name, id='567', eta=datetime.now(timezone.utc) + timedelta(hours=4)
        )
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertFalse(
            f'flower_task_prefetch_time_seconds{{task="{task_name}",worker="{worker_name}"}} ' in metrics
        )

    def test_worker_online_metric_worker_is_offline(self):
        state = EventsState()
        worker_name = 'worker1'
        state.get_or_create_worker(worker_name)
        events = [Event('worker-offline', hostname=worker_name)]
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(f'flower_worker_online{{worker="{worker_name}"}} 0.0' in metrics)

    def test_metrics_purge_expired_worker(self):
        state = EventsState()
        worker_name = 'expired-worker-for-metrics-purge'
        task_name = 'task-for-metrics-purge'
        old_timestamp = time.time() - 3600
        state.event(Event(
            'worker-heartbeat', hostname=worker_name,
            timestamp=old_timestamp, local_received=old_timestamp,
            freq=2, active=1))
        state.metrics.events.labels(
            worker_name, 'task-succeeded', task_name).inc()
        state.metrics.runtime.labels(worker_name, task_name).observe(1)
        state.metrics.prefetch_time.labels(worker_name, task_name).set(1)
        state.metrics.number_of_prefetched_tasks.labels(
            worker_name, task_name).set(1)
        self._app.events.state = state
        self._app.inspector.workers[worker_name] = {'stats': {}}

        self.assertFalse(state.workers[worker_name].alive)
        with self.mock_option('purge_offline_workers', 60):
            metrics = self.get('/metrics').body.decode('utf-8')
            next_metrics = self.get('/metrics').body.decode('utf-8')

        self.assertNotIn(worker_name, metrics)
        self.assertNotIn(worker_name, next_metrics)
        self.assertIn(worker_name, state.counter)
        self.assertIn(worker_name, state.workers)
        self.assertIn(worker_name, self._app.inspector.workers)

    def test_metrics_keep_live_worker(self):
        state = EventsState()
        worker_name = 'live-worker-for-metrics-purge'
        timestamp = time.time()
        state.event(Event(
            'worker-heartbeat', hostname=worker_name,
            timestamp=timestamp, local_received=timestamp,
            freq=2, active=1))
        self._app.events.state = state
        self._app.inspector.workers[worker_name] = {'stats': {}}

        with self.mock_option('purge_offline_workers', 60):
            metrics = self.get('/metrics').body.decode('utf-8')

        self.assertIn(
            f'flower_worker_online{{worker="{worker_name}"}} 1.0', metrics)
        self.assertIn(worker_name, state.counter)
        self.assertIn(worker_name, state.workers)
        self.assertIn(worker_name, self._app.inspector.workers)

    def test_metrics_purge_worker_without_heartbeat_metric(self):
        state = EventsState()
        worker_name = 'task-only-worker-for-metrics-purge'
        task_name = 'task-for-worker-without-heartbeat'
        state.get_or_create_worker(worker_name)
        state.counter[worker_name]['task-succeeded'] += 1
        state.metrics.events.labels(
            worker_name, 'task-succeeded', task_name).inc()
        self._app.events.state = state

        with self.mock_option('purge_offline_workers', 60):
            metrics = self.get('/metrics').body.decode('utf-8')

        self.assertNotIn(worker_name, metrics)

    def test_worker_prefetched_tasks_metric(self):
        state = EventsState()
        worker_name = 'worker2'
        task_name = 'task1'
        task_id = uuid()
        state.get_or_create_worker(worker_name)
        events = [
            Event(
                'task-received',
                uuid=task_id,
                name=task_name,
                args='(2, 2)',
                kwargs="{'foo': 'bar'}",
                retries=1,
                eta=None,
                hostname=worker_name
            ),
            Event(
                'task-received',
                uuid=uuid(),
                name=task_name,
                args='(2, 2)',
                kwargs="{'foo': 'bar'}",
                retries=1,
                eta=None,
                hostname=worker_name
            ),
            Event('task-started', uuid=task_id, hostname=worker_name),
        ]

        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)
        self._app.events.state = state

        metrics = self.get('/metrics').body.decode('utf-8')

        self.assertTrue(
            f'flower_worker_prefetched_tasks{{task="{task_name}",worker="{worker_name}"}} 1.0' in metrics
        )

    def gauge_after(self, *events):
        # metrics are process-wide, a fresh task name keeps each test's labels apart
        task_name = 'task-' + uuid()
        state = EventsState()
        state.get_or_create_worker('worker1')
        received = Event('task-received', uuid='1', name=task_name, args='()', kwargs='{}',
                         retries=0, eta=None, hostname='worker1')
        for i, event in enumerate((received, *events)):
            event['clock'] = i
            event['local_received'] = time.time()
            state.event(event)
        self._app.events.state = state
        metrics = self.get('/metrics').body.decode('utf-8')
        line = next(l for l in metrics.splitlines()
                    if l.startswith(f'flower_worker_prefetched_tasks{{task="{task_name}",worker="worker1"}}'))
        return float(line.split()[-1])

    def test_received_task_counts_as_prefetched(self):
        self.assertEqual(1.0, self.gauge_after())

    def test_started_task_leaves_the_prefetch_queue(self):
        self.assertEqual(0.0, self.gauge_after(Event('task-started', uuid='1', hostname='worker1')))

    def test_task_revoked_before_start_leaves_the_prefetch_queue(self):
        self.assertEqual(0.0, self.gauge_after(
            Event('task-revoked', uuid='1', hostname='worker1', terminated=False, expired=True)))

    def test_task_rejected_before_start_leaves_the_prefetch_queue(self):
        self.assertEqual(0.0, self.gauge_after(
            Event('task-rejected', uuid='1', hostname='worker1', requeue=False)))

    def test_task_revoked_after_start_is_not_counted_twice(self):
        self.assertEqual(0.0, self.gauge_after(
            Event('task-started', uuid='1', hostname='worker1'),
            Event('task-revoked', uuid='1', hostname='worker1', terminated=True, expired=False)))


class HealthcheckTests(AsyncHTTPTestCase):
    def test_healthcheck_route(self):
        response = self.get('/healthcheck').body.decode('utf-8')
        self.assertEqual(response, 'OK')
