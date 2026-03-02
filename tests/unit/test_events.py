import queue
import time
import unittest
from unittest.mock import MagicMock, patch

from celery.events import Event
from tornado.ioloop import IOLoop

from flower.events import Events, EventsState, get_prometheus_metrics

import celery


class TestEventsState(unittest.TestCase):
    def test_counter_tracks_events_by_worker(self):
        state = EventsState()
        state.get_or_create_worker('w1')
        e = Event('worker-online', hostname='w1')
        e['clock'] = 0
        e['local_received'] = time.time()
        state.event(e)

        self.assertIn('w1', state.counter)
        self.assertEqual(state.counter['w1']['worker-online'], 1)

    def test_counter_increments(self):
        state = EventsState()
        state.get_or_create_worker('w1')
        for i in range(5):
            e = Event('worker-heartbeat', hostname='w1', active=0)
            e['clock'] = i
            e['local_received'] = time.time()
            state.event(e)

        self.assertEqual(state.counter['w1']['worker-heartbeat'], 5)


class TestPrometheusMetricsRemoval(unittest.TestCase):
    """Test remove_worker_metrics using the global singleton to avoid
    duplicate registry errors from prometheus_client."""

    def test_remove_worker_metrics_clears_labels(self):
        metrics = get_prometheus_metrics()
        metrics.worker_online.labels('test_remove_w1').set(1)
        metrics.worker_online.labels('test_remove_w2').set(1)

        self.assertIn(('test_remove_w1',), metrics.worker_online._metrics)

        metrics.remove_worker_metrics('test_remove_w1')

        self.assertNotIn(('test_remove_w1',), metrics.worker_online._metrics)
        self.assertIn(('test_remove_w2',), metrics.worker_online._metrics)

    def test_remove_nonexistent_worker_is_noop(self):
        metrics = get_prometheus_metrics()
        # Should not raise
        metrics.remove_worker_metrics('test_remove_nonexistent_worker_xyz')

    def test_remove_multi_label_metrics(self):
        metrics = get_prometheus_metrics()
        metrics.runtime.labels('test_remove_mw1', 'task1').observe(1.0)
        metrics.runtime.labels('test_remove_mw1', 'task2').observe(2.0)
        metrics.runtime.labels('test_remove_mw2', 'task1').observe(3.0)

        metrics.remove_worker_metrics('test_remove_mw1')

        remaining_keys = list(metrics.runtime._metrics.keys())
        for key in remaining_keys:
            self.assertNotEqual(key[0], 'test_remove_mw1')
        self.assertIn(('test_remove_mw2', 'task1'), metrics.runtime._metrics)

    def test_remove_handles_missing_private_attr(self):
        metrics = get_prometheus_metrics()
        # Temporarily remove _metrics to simulate missing attr
        original = metrics.worker_online._metrics
        try:
            del metrics.worker_online._metrics
            # Should not raise — getattr guard should catch it
            metrics.remove_worker_metrics('w1')
        finally:
            metrics.worker_online._metrics = original


class TestEventsBackpressure(unittest.TestCase):
    def test_on_event_drops_when_queue_full(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop)
        # Fill the queue
        for i in range(events._BACKPRESSURE_MAXSIZE):
            events.on_event({'hostname': 'w1', 'type': 'worker-heartbeat'})

        # Next event should be dropped without raising
        events.on_event({'hostname': 'w1', 'type': 'worker-heartbeat'})
        self.assertEqual(events._event_queue.qsize(), events._BACKPRESSURE_MAXSIZE)

    def test_drop_logging_is_rate_limited(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop)
        # Fill the queue
        for i in range(events._BACKPRESSURE_MAXSIZE):
            events.on_event({'hostname': 'w1', 'type': 'worker-heartbeat'})

        # Reset drop state so we control it entirely within the patch.
        # Set _last_drop_log_time far enough in the past to guarantee the
        # 5-second cooldown has elapsed (time.monotonic() can be small on
        # short-lived processes).
        events._drop_count = 0
        events._last_drop_log_time = time.monotonic() - 10.0

        with patch('flower.events.logger') as mock_logger:
            # First drop should trigger a log (cooldown elapsed)
            events.on_event({'hostname': 'w1', 'type': 'worker-heartbeat'})
            self.assertEqual(mock_logger.warning.call_count, 1)

            # Subsequent drops within 5s should NOT trigger more logs
            for _ in range(99):
                events.on_event({'hostname': 'w1', 'type': 'worker-heartbeat'})
            self.assertEqual(mock_logger.warning.call_count, 1)

    def test_drain_events_processes_batch(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop)
        events.state = MagicMock()

        for i in range(10):
            events._event_queue.put({'hostname': 'w1', 'type': 'worker-heartbeat',
                                     'clock': i, 'local_received': time.time()})

        events._drain_events()

        self.assertEqual(events.state.event.call_count, 10)
        self.assertTrue(events._event_queue.empty())

    def test_drain_events_handles_errors_gracefully(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop)
        events.state = MagicMock()
        events.state.event.side_effect = [RuntimeError("test"), None]

        events._event_queue.put({'hostname': 'w1', 'type': 'a'})
        events._event_queue.put({'hostname': 'w1', 'type': 'b'})

        events._drain_events()

        # Both events should be consumed despite the error on the first one
        self.assertEqual(events.state.event.call_count, 2)
        self.assertTrue(events._event_queue.empty())

    def test_drain_respects_batch_size(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop)
        events.state = MagicMock()

        count = events._DRAIN_BATCH_SIZE + 100
        for i in range(count):
            events._event_queue.put({'hostname': 'w1', 'type': 'hb'})

        events._drain_events()

        # Should process exactly _DRAIN_BATCH_SIZE, leaving 100
        self.assertEqual(events.state.event.call_count, events._DRAIN_BATCH_SIZE)
        self.assertEqual(events._event_queue.qsize(), 100)


class TestEventsRetryBackoff(unittest.TestCase):
    def test_retry_interval_caps_at_max(self):
        from flower.events import MAX_RETRY_INTERVAL
        try_interval = 1
        for _ in range(100):
            try_interval *= 2
            if try_interval > MAX_RETRY_INTERVAL:
                try_interval = MAX_RETRY_INTERVAL

        self.assertEqual(try_interval, MAX_RETRY_INTERVAL)
        self.assertEqual(MAX_RETRY_INTERVAL, 60)


class TestEventsStopSafety(unittest.TestCase):
    def test_stop_calls_save_state_even_if_timer_fails(self):
        capp = celery.Celery()
        io_loop = MagicMock()
        events = Events(capp, io_loop, persistent=True, db='test_db')

        events.timer = MagicMock()
        events.timer.stop.side_effect = RuntimeError("timer error")
        events.state_save_timer = MagicMock()
        events.state_save_timer.stop.side_effect = RuntimeError("save timer error")
        events._drain_timer = MagicMock()
        events._drain_timer.stop.side_effect = RuntimeError("drain timer error")

        with patch.object(events, 'save_state') as mock_save:
            events.stop()
            mock_save.assert_called_once()


if __name__ == '__main__':
    unittest.main()
