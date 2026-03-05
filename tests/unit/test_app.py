import time
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import celery
from celery.events import Event
from celery.events.state import Worker
from tornado.ioloop import IOLoop
from tornado.options import options

from flower import command  # noqa: F401 side effect - define options
from flower.app import Flower
from flower.events import Events, EventsState, get_prometheus_metrics
from flower.urls import handlers, settings


class TestPurgeOfflineWorkers(unittest.TestCase):
    def setUp(self):
        capp = celery.Celery()
        events = Events(capp, IOLoop.current())
        self.app = Flower(capp=capp, events=events,
                          options=options, handlers=handlers, **settings)
        self._orig_purge = options.purge_offline_workers

    def tearDown(self):
        options.purge_offline_workers = self._orig_purge

    def test_purge_removes_offline_workers(self):
        state = EventsState()
        w, _ = state.get_or_create_worker('w1')
        state.counter['w1']['worker-online'] = 1
        w.heartbeats = [time.time() - 3600]
        self.app.events.state = state

        self.app.options.purge_offline_workers = 60
        with patch.object(Worker, 'alive', new_callable=PropertyMock, return_value=False):
            self.app._purge_offline_workers()

        self.assertNotIn('w1', state.counter)

    def test_purge_keeps_alive_workers(self):
        state = EventsState()
        w, _ = state.get_or_create_worker('w1')
        state.counter['w1']['worker-online'] = 1
        w.heartbeats = [time.time()]
        self.app.events.state = state

        self.app.options.purge_offline_workers = 60
        with patch.object(Worker, 'alive', new_callable=PropertyMock, return_value=True):
            self.app._purge_offline_workers()

        self.assertIn('w1', state.counter)

    def test_purge_keeps_recently_offline_workers(self):
        state = EventsState()
        w, _ = state.get_or_create_worker('w1')
        state.counter['w1']['worker-online'] = 1
        w.heartbeats = [time.time() - 10]  # 10 seconds ago
        self.app.events.state = state

        self.app.options.purge_offline_workers = 60  # threshold 60s
        with patch.object(Worker, 'alive', new_callable=PropertyMock, return_value=False):
            self.app._purge_offline_workers()

        self.assertIn('w1', state.counter)

    def test_purge_removes_orphaned_counter_entries(self):
        state = EventsState()
        state.counter['orphan_worker']['worker-online'] = 1
        self.app.events.state = state

        self.app.options.purge_offline_workers = 60
        self.app._purge_offline_workers()

        self.assertNotIn('orphan_worker', state.counter)

    def test_purge_removes_orphaned_inspector_entries(self):
        state = EventsState()
        self.app.events.state = state
        self.app.inspector.workers['orphan_worker'] = {'stats': {}}

        self.app.options.purge_offline_workers = 60
        self.app._purge_offline_workers()

        self.assertNotIn('orphan_worker', self.app.inspector.workers)

    def test_purge_noop_when_threshold_is_none(self):
        state = EventsState()
        state.counter['w1']['worker-online'] = 1
        self.app.events.state = state

        self.app.options.purge_offline_workers = None
        self.app._purge_offline_workers()

        self.assertIn('w1', state.counter)

    def test_purge_cleans_prometheus_metrics(self):
        state = EventsState()
        w, _ = state.get_or_create_worker('test_purge_prom_w1')
        state.counter['test_purge_prom_w1']['worker-online'] = 1
        w.heartbeats = [time.time() - 3600]
        metrics = get_prometheus_metrics()
        metrics.worker_online.labels('test_purge_prom_w1').set(1)
        self.app.events.state = state

        self.app.options.purge_offline_workers = 60
        with patch.object(Worker, 'alive', new_callable=PropertyMock, return_value=False):
            self.app._purge_offline_workers()

        self.assertNotIn(('test_purge_prom_w1',), metrics.worker_online._metrics)


if __name__ == '__main__':
    unittest.main()
