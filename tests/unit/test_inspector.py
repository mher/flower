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


class InspectorMaskedSettingsTests(TestCase):
    conf = {
        'broker_url': 'redis://localhost:6379/0',
        'SENTRY_DSN': 'https://secret@sentry.example.com/1',
        'broker_transport_options': {'master_name': 'mymaster', 'socket_timeout': 5},
    }

    def test_settings_are_unchanged_by_default(self):
        inspector = Inspector(Mock(), Mock(), timeout=1)

        inspector._on_update('worker1', 'conf', self.conf)

        self.assertIs(self.conf, inspector.workers['worker1']['conf'])

    def test_ignores_empty_setting_names(self):
        inspector = Inspector(Mock(), Mock(), timeout=1, masked_settings=['', ' '])

        inspector._on_update('worker1', 'conf', self.conf)

        self.assertIs(self.conf, inspector.workers['worker1']['conf'])

    def test_masks_settings_by_name_case_insensitively(self):
        inspector = Inspector(Mock(), Mock(), timeout=1,
                              masked_settings=['sentry_dsn', ' Master_Name '])

        inspector._on_update('worker1', 'conf', self.conf)

        self.assertEqual({
            'broker_url': 'redis://localhost:6379/0',
            'SENTRY_DSN': '********',
            'broker_transport_options': {'master_name': '********', 'socket_timeout': 5},
        }, inspector.workers['worker1']['conf'])
        self.assertEqual('mymaster', self.conf['broker_transport_options']['master_name'])

    def test_masks_whole_nested_setting(self):
        inspector = Inspector(Mock(), Mock(), timeout=1,
                              masked_settings=['broker_transport_options'])

        inspector._on_update('worker1', 'conf', self.conf)

        self.assertEqual('********', inspector.workers['worker1']['conf']['broker_transport_options'])

    def test_masks_only_conf_responses(self):
        inspector = Inspector(Mock(), Mock(), timeout=1, masked_settings=['sentry_dsn'])
        stats = {'SENTRY_DSN': 'not a setting'}

        inspector._on_update('worker1', 'stats', stats)

        self.assertEqual('not a setting', inspector.workers['worker1']['stats']['SENTRY_DSN'])


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

    async def test_global_refresh_does_not_satisfy_worker_refresh(self):
        # the global refresh skips the task lists a worker page needs
        inspector = Inspector(Mock(), Mock(), timeout=1)
        complete = asyncio.Event()

        async def inspect_all(_):
            await complete.wait()

        inspector._inspect_all = inspect_all

        all_workers = inspector.inspect()
        one_worker = inspector.inspect('worker1')

        self.assertIsNot(all_workers, one_worker)
        complete.set()
        await all_workers
        await one_worker

    async def test_global_refresh_skips_task_lists(self):
        inspector = Inspector(Mock(), Mock(), timeout=1)
        called = []

        async def inspect_method(method, workername):
            called.append((method, workername))

        inspector._inspect_method = inspect_method
        await inspector.inspect()

        self.assertEqual(
            [('stats', None), ('active_queues', None), ('registered', None), ('conf', None)],
            called)

    async def test_worker_refresh_runs_every_method(self):
        inspector = Inspector(Mock(), Mock(), timeout=1)
        called = []

        async def inspect_method(method, workername):
            called.append(method)

        inspector._inspect_method = inspect_method
        await inspector.inspect('worker1')

        self.assertEqual(list(Inspector.inspect_methods), called)

    async def test_bounds_inspector_concurrency(self):
        io_loop = Mock()
        pending = []

        def run_in_executor(*_):
            future = asyncio.get_running_loop().create_future()
            pending.append(future)
            return future

        io_loop.run_in_executor.side_effect = run_in_executor
        inspector = Inspector(io_loop, Mock(), timeout=1, max_concurrency=2)
        inspector.inspect_methods = ('stats', 'active', 'conf')

        operation = inspector.inspect('worker1')
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
