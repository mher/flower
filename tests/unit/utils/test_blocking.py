import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor

from kombu.exceptions import OperationalError
from tornado.testing import AsyncTestCase, gen_test
from tornado.web import HTTPError

from flower.utils.blocking import BlockingOperationRunner


class BlockingOperationRunnerTests(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.executor = ThreadPoolExecutor(max_workers=4)

    def tearDown(self):
        self.executor.shutdown(wait=True)
        super().tearDown()

    @gen_test
    async def test_runs_operation_in_executor_and_logs_elapsed_time(self):
        runner = BlockingOperationRunner(self.executor)
        io_loop_thread = threading.get_ident()

        with self.assertLogs('flower.utils.blocking', level='DEBUG') as logs:
            worker_thread = await runner.run(
                'test.operation', 'test-target', threading.get_ident)

        self.assertNotEqual(io_loop_thread, worker_thread)
        self.assertIn("test.operation", logs.output[0])
        self.assertIn("test-target", logs.output[0])
        self.assertIn("completed in", logs.output[0])

    @gen_test
    async def test_converts_connection_errors_to_service_unavailable(self):
        runner = BlockingOperationRunner(self.executor)

        def fail():
            raise OperationalError('broker is down')

        with self.assertLogs('flower.utils.blocking', level='WARNING'):
            with self.assertRaises(HTTPError) as raised:
                await runner.run('test.operation', 'test-target', fail)

        self.assertEqual(503, raised.exception.status_code)

    @gen_test
    async def test_supports_backend_specific_connection_errors(self):
        runner = BlockingOperationRunner(self.executor)

        class BackendConnectionError(Exception):
            pass

        def fail():
            raise BackendConnectionError('backend is down')

        with self.assertLogs('flower.utils.blocking', level='WARNING'):
            with self.assertRaises(HTTPError) as raised:
                await runner.run(
                    'test.operation', 'test-target', fail,
                    connection_errors=(BackendConnectionError,))

        self.assertEqual(503, raised.exception.status_code)

    @gen_test
    async def test_converts_unexpected_errors_to_internal_server_error(self):
        runner = BlockingOperationRunner(self.executor)

        def fail():
            raise ValueError('unexpected')

        with self.assertLogs('flower.utils.blocking', level='ERROR'):
            with self.assertRaises(HTTPError) as raised:
                await runner.run('test.operation', 'test-target', fail)

        self.assertEqual(500, raised.exception.status_code)
        self.assertIsInstance(raised.exception.__cause__, ValueError)

    @gen_test
    async def test_limits_concurrent_operations_before_executor_submission(self):
        class PausedExecutor:
            def __init__(self):
                self.futures = []
                self.two_submitted = asyncio.Event()
                self.three_submitted = asyncio.Event()

            def submit(self, _func, *_args, **_kwargs):
                future = Future()
                self.futures.append(future)
                if len(self.futures) == 2:
                    self.two_submitted.set()
                elif len(self.futures) == 3:
                    self.three_submitted.set()
                return future

        executor = PausedExecutor()
        runner = BlockingOperationRunner(executor, max_concurrency=2)

        operations = [
            asyncio.create_task(runner.run('test.operation', index, lambda: None))
            for index in range(3)
        ]
        await asyncio.wait_for(executor.two_submitted.wait(), timeout=1)

        self.assertEqual(2, len(executor.futures))
        executor.futures[0].set_result(None)
        await asyncio.wait_for(executor.three_submitted.wait(), timeout=1)
        self.assertEqual(3, len(executor.futures))

        executor.futures[1].set_result(None)
        executor.futures[2].set_result(None)
        await asyncio.gather(*operations)
