import asyncio
import logging
import time
from functools import partial

from celery.exceptions import BackendError
from kombu.exceptions import ConnectionError as KombuConnectionError
from kombu.exceptions import OperationalError
from tornado.web import HTTPError


logger = logging.getLogger(__name__)


CONNECTION_ERRORS = (
    BackendError,
    ConnectionError,
    KombuConnectionError,
    OperationalError,
    TimeoutError,
)


class BlockingOperationRunner:
    """Run dependency calls without blocking Tornado's I/O loop."""

    max_blocking_operations = 5

    def __init__(self, executor=None, max_concurrency=None):
        max_concurrency = max_concurrency or self.max_blocking_operations
        self.executor = executor
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, operation, target, func, *args,
                  connection_errors=(), **kwargs):
        started = time.monotonic()
        try:
            async with self.semaphore:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    self.executor, partial(func, *args, **kwargs))
        except CONNECTION_ERRORS + tuple(connection_errors) as exc:
            elapsed = time.monotonic() - started
            logger.warning(
                "Blocking operation '%s' for '%s' failed after %.3fs: %s",
                operation, target, elapsed, exc)
            raise HTTPError(503, 'Broker or result backend unavailable') from exc
        except Exception as exc:
            elapsed = time.monotonic() - started
            logger.exception(
                "Blocking operation '%s' for '%s' failed after %.3fs",
                operation, target, elapsed)
            raise HTTPError(500) from exc

        elapsed = time.monotonic() - started
        logger.debug(
            "Blocking operation '%s' for '%s' completed in %.3fs",
            operation, target, elapsed)
        return result
