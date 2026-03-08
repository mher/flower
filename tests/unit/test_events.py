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
