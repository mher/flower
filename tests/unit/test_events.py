import asyncio
import os
import shelve
import tempfile
from unittest.mock import Mock

from kombu.exceptions import OperationalError
from tornado.testing import AsyncTestCase, gen_test

from flower.events import Events


class PersistenceTests(AsyncTestCase):
    def events(self, db):
        return Events(Mock(), self.io_loop, db=db, persistent=True,
                      enable_events=False)

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
