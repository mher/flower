import asyncio
import dbm
import dbm.dumb
import os
import shelve
import tempfile
import time
from unittest.mock import Mock, patch

from kombu.exceptions import OperationalError
from tornado.testing import AsyncTestCase, gen_test

from flower.events import Events
from tests.unit.utils import task_succeeded_events


class PersistenceTests(AsyncTestCase):
    def events(self, db, max_tasks_in_memory=10, **kwargs):
        return Events(Mock(), self.io_loop, db=db, persistent=True,
                      enable_events=False,
                      max_tasks_in_memory=max_tasks_in_memory, **kwargs)

    def test_recovers_counters_and_continues_counting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db)
            events.state.counter['worker1']['task-received'] = 2
            events.state.counter['worker1']['task-succeeded'] = 1
            events.state.counter['worker2']['task-failed'] = 3
            events.save_state()

            restored = self.events(db)

            self.assertEqual(
                2, restored.state.counter['worker1']['task-received'])
            self.assertEqual(
                1, restored.state.counter['worker1']['task-succeeded'])
            self.assertEqual(
                3, restored.state.counter['worker2']['task-failed'])

            restored.state.counter['worker1']['task-succeeded'] += 1
            restored.state.counter['worker3']['task-received'] += 1
            restored.save_state()

            restored_again = self.events(db)
            self.assertEqual(
                2, restored_again.state.counter['worker1']['task-succeeded'])
            self.assertEqual(
                1, restored_again.state.counter['worker3']['task-received'])

    def test_failed_save_preserves_previous_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db)
            events.state.counter['worker1']['task-received'] = 2
            events.save_state()

            events.state.counter['worker1']['task-received'] = 5
            events.state.counter['worker1']['unpicklable'] = lambda: None
            with self.assertRaises(Exception):
                events.save_state()

            restored = self.events(db)
            self.assertEqual(
                2, restored.state.counter['worker1']['task-received'])

    def test_save_leaves_no_temporary_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db)
            events.state.counter['worker1']['task-received'] = 1
            events.save_state()

            leftovers = [f for f in os.listdir(tmpdir) if '.tmp' in f]
            self.assertEqual([], leftovers)

    def test_recovers_from_corrupt_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            with open(db, 'wb') as f:
                f.write(b'garbage' * 100)

            with self.assertLogs('flower.events', level='ERROR'):
                events = self.events(db)

            self.assertEqual({}, dict(events.state.counter))
            self.assertTrue(os.path.exists(db + '.corrupt'))

            events.state.counter['worker1']['task-received'] = 7
            events.save_state()
            restored = self.events(db)
            self.assertEqual(
                7, restored.state.counter['worker1']['task-received'])

    def test_save_state_with_suffixed_db_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            with patch.object(dbm, '_defaultmod', dbm.dumb):
                events = self.events(db)
                events.state.counter['worker1']['task-received'] = 3
                events.save_state()

                self.assertTrue(os.path.exists(db + '.dat'))
                self.assertFalse(os.path.exists(db))
                leftovers = [f for f in os.listdir(tmpdir) if '.tmp' in f]
                self.assertEqual([], leftovers)

                restored = self.events(db)
                self.assertEqual(
                    3, restored.state.counter['worker1']['task-received'])

    def test_recovers_from_corrupt_suffixed_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            for suffix in ('.dat', '.dir'):
                with open(db + suffix, 'wb') as f:
                    f.write(b'garbage' * 100)

            with patch.object(dbm, '_defaultmod', dbm.dumb):
                with self.assertLogs('flower.events', level='ERROR'):
                    events = self.events(db)

                self.assertEqual({}, dict(events.state.counter))
                self.assertTrue(os.path.exists(db + '.dat.corrupt'))
                self.assertTrue(os.path.exists(db + '.dir.corrupt'))

    def test_warns_when_save_dominates_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db, state_save_interval=1000)

            with self.assertLogs('flower.events', level='WARNING') as logs:
                for _ in range(3):
                    with patch('flower.events.time.monotonic', side_effect=[0, 60]):
                        events.save_state()

            self.assertEqual(3, len(logs.output))
            self.assertIn('--state-save-interval', logs.output[0])

    def test_no_warning_for_fast_saves(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db, state_save_interval=1000)

            with (
                patch('flower.events.time.monotonic', side_effect=[0, 0.01]),
                self.assertNoLogs('flower.events', level='WARNING'),
            ):
                events.save_state()

    def test_no_warning_without_save_timer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db)

            with (
                patch('flower.events.time.monotonic', side_effect=[0, 60]),
                self.assertNoLogs('flower.events', level='WARNING'),
            ):
                events.save_state()

    def receive_tasks(self, events, count):
        for _ in range(count):
            for event in task_succeeded_events('worker1'):
                event['clock'] = len(events.state.tasks)
                event['local_received'] = time.time()
                events.state.event(event)

    def test_raises_task_limit_on_restore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db, max_tasks_in_memory=2)
            self.receive_tasks(events, 2)
            events.save_state()

            restored = self.events(db, max_tasks_in_memory=4)
            self.receive_tasks(restored, 2)

            self.assertEqual(4, len(restored.state.tasks))

    def test_shrinks_task_limit_on_restore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db, max_tasks_in_memory=4)
            self.receive_tasks(events, 4)
            events.save_state()

            restored = self.events(db, max_tasks_in_memory=2)

            self.assertEqual(2, len(restored.state.tasks))
            self.receive_tasks(restored, 1)
            self.assertEqual(2, len(restored.state.tasks))

    def test_loads_database_without_persisted_counters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = os.path.join(tmpdir, 'flower')
            events = self.events(db)
            events.state.counter['worker1']['task-succeeded'] = 1
            with shelve.open(db, flag='n') as state:
                state['events'] = events.state

            restored = self.events(db)

            self.assertEqual({}, dict(restored.state.counter))


class EnableEventsTests(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.events = Events.__new__(Events)
        self.events.io_loop = Mock()
        self.events.capp = Mock()

    @gen_test
    async def test_awaits_enable_events_call(self):
        future = asyncio.Future()
        self.events.io_loop.run_in_executor.return_value = future

        operation = asyncio.create_task(self.events.on_enable_events())
        await asyncio.sleep(0)

        self.events.io_loop.run_in_executor.assert_called_once_with(
            None, self.events.capp.control.enable_events)
        self.assertFalse(operation.done())

        future.set_result(None)
        await operation

    @gen_test
    async def test_logs_enable_events_failure_without_traceback(self):
        future = asyncio.Future()
        self.events.io_loop.run_in_executor.return_value = future

        operation = asyncio.create_task(self.events.on_enable_events())
        await asyncio.sleep(0)
        future.set_exception(OperationalError('broker is down'))

        with self.assertLogs('flower.events', level='WARNING') as logs:
            await operation

        self.assertEqual(
            'WARNING:flower.events:Failed to enable events: broker is down',
            logs.output[0])
