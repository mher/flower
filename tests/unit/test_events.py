import asyncio
from unittest.mock import Mock

from kombu.exceptions import OperationalError
from tornado.testing import AsyncTestCase, gen_test

from flower.events import Events


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
