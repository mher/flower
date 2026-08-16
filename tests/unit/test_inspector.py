import asyncio
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock

from kombu.exceptions import OperationalError

from flower.inspector import Inspector


# pylint: disable=protected-access
class InspectorTests(TestCase):
    def test_logs_broker_failure_without_propagating_it(self):
        capp = Mock()
        capp.control.inspect.return_value.registered.side_effect = (
            OperationalError('broker is down'))
        inspector = Inspector(Mock(), capp, timeout=1)

        with self.assertLogs('flower.inspector', level='WARNING') as logs:
            inspector._inspect('registered', None)

        self.assertEqual(
            'WARNING:flower.inspector:'
            'Inspect method registered failed: broker is down',
            logs.output[0],
        )

    def test_handles_transport_specific_connection_error(self):
        class TransportConnectionError(Exception):
            pass

        capp = Mock()
        capp.control.inspect.return_value.active.side_effect = (
            TransportConnectionError('connection closed by server'))
        connection = capp.connection_for_read.return_value
        connection.recoverable_connection_errors = (
            TransportConnectionError,)
        inspector = Inspector(Mock(), capp, timeout=1)

        with self.assertLogs('flower.inspector', level='WARNING') as logs:
            inspector._inspect('active', None)

        self.assertEqual(
            'WARNING:flower.inspector:'
            'Inspect method active failed: connection closed by server',
            logs.output[0],
        )
        connection.close.assert_called_once_with()


class InspectorConcurrencyTests(IsolatedAsyncioTestCase):
    async def test_coalesces_refreshes_for_the_same_worker(self):
        inspector = Inspector(Mock(), Mock(), timeout=1)
        complete = asyncio.Event()

        async def inspect_all(_):
            await complete.wait()

        inspector._inspect_all = inspect_all

        first = inspector.inspect('worker1')
        second = inspector.inspect('worker1')

        self.assertIs(first, second)
        complete.set()
        await first

    async def test_global_refresh_satisfies_worker_refresh(self):
        inspector = Inspector(Mock(), Mock(), timeout=1)
        complete = asyncio.Event()

        async def inspect_all(_):
            await complete.wait()

        inspector._inspect_all = inspect_all

        all_workers = inspector.inspect()
        one_worker = inspector.inspect('worker1')

        self.assertIs(all_workers, one_worker)
        complete.set()
        await all_workers

    async def test_bounds_inspector_concurrency(self):
        io_loop = Mock()
        pending = []

        def run_in_executor(*_):
            future = asyncio.get_running_loop().create_future()
            pending.append(future)
            return future

        io_loop.run_in_executor.side_effect = run_in_executor
        inspector = Inspector(io_loop, Mock(), timeout=1, max_concurrency=2)
        inspector.methods = ('stats', 'active', 'conf')

        operation = inspector.inspect()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(2, len(pending))

        pending[0].set_result(None)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(3, len(pending))

        pending[1].set_result(None)
        pending[2].set_result(None)
        await operation
