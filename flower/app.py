import sys
import logging
import time

from concurrent.futures import ThreadPoolExecutor

import celery
import tornado.web

from tornado import ioloop
from tornado.httpserver import HTTPServer
from tornado.ioloop import PeriodicCallback
from tornado.web import url

from .urls import handlers as default_handlers
from .events import Events
from .inspector import Inspector
from .options import default_options


logger = logging.getLogger(__name__)


if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# pylint: disable=consider-using-f-string
def rewrite_handler(handler, url_prefix):
    if isinstance(handler, url):
        return url("/{}{}".format(url_prefix.strip("/"), handler.regex.pattern),
                   handler.handler_class, handler.kwargs, handler.name)
    return ("/{}{}".format(url_prefix.strip("/"), handler[0]), handler[1])


class Flower(tornado.web.Application):
    pool_executor_cls = ThreadPoolExecutor
    max_workers = None

    def __init__(self, options=None, capp=None, events=None,
                 io_loop=None, **kwargs):
        handlers = default_handlers
        if options is not None and options.url_prefix:
            handlers = [rewrite_handler(h, options.url_prefix) for h in handlers]
        kwargs.update(handlers=handlers)
        super().__init__(**kwargs)
        self.options = options or default_options
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.ssl_options = kwargs.get('ssl_options', None)

        self.capp = capp or celery.Celery()
        self.capp.loader.import_default_modules()

        self.executor = self.pool_executor_cls(max_workers=self.max_workers)
        self.io_loop.set_default_executor(self.executor)

        self.inspector = Inspector(self.io_loop, self.capp, self.options.inspect_timeout / 1000.0)

        self.events = events or Events(
            self.capp,
            db=self.options.db,
            persistent=self.options.persistent,
            state_save_interval=self.options.state_save_interval,
            enable_events=self.options.enable_events,
            io_loop=self.io_loop,
            max_workers_in_memory=self.options.max_workers,
            max_tasks_in_memory=self.options.max_tasks)
        self.started = False
        self._purge_timer = None

    def start(self):
        self.events.start()

        if not self.options.unix_socket:
            self.listen(self.options.port, address=self.options.address,
                        ssl_options=self.ssl_options,
                        xheaders=self.options.xheaders)
        else:
            from tornado.netutil import bind_unix_socket
            server = HTTPServer(self)
            socket = bind_unix_socket(self.options.unix_socket, mode=0o777)
            server.add_socket(socket)

        self.started = True
        self.update_workers()

        if self.options.purge_offline_workers is not None:
            interval_ms = max(self.options.purge_offline_workers * 1000, 10000)
            self._purge_timer = PeriodicCallback(self._purge_offline_workers,
                                                 interval_ms)
            self._purge_timer.start()

        self.io_loop.start()

    def stop(self):
        if self.started:
            self.events.stop()
            if self._purge_timer:
                self._purge_timer.stop()
            logging.debug("Stopping executors...")
            self.executor.shutdown(wait=False)
            logging.debug("Stopping event loop...")
            self.io_loop.stop()
            self.started = False

    @property
    def transport(self):
        return getattr(self.capp.connection().transport, 'driver_type', None)

    @property
    def workers(self):
        return self.inspector.workers

    def update_workers(self, workername=None):
        return self.inspector.inspect(workername)

    def _purge_offline_workers(self):
        """Purge workers that have been offline beyond the threshold.

        Handles two cases:
        - Workers present in state.workers: check alive status + heartbeat age
        - Orphaned entries (in counter/inspector but not state.workers): always purge
        """
        threshold = self.options.purge_offline_workers
        if threshold is None:
            return

        now = time.time()
        state = self.events.state

        # Collect all known worker names from state.counter and inspector.workers
        all_worker_names = set(state.counter.keys()) | set(self.inspector.workers.keys())

        for worker_name in all_worker_names:
            worker = state.workers.get(worker_name)
            if worker is not None:
                # Skip workers that are still alive
                if worker.alive:
                    continue

                # Check if the worker has been offline beyond the threshold
                heartbeats = getattr(worker, 'heartbeats', [])
                if heartbeats:
                    last_heartbeat = max(heartbeats)
                    if now - last_heartbeat <= threshold:
                        continue
            # else: worker not in state.workers — orphaned entry, always purge

            # Purge from state.counter
            state.counter.pop(worker_name, None)

            # Purge Prometheus metrics for this worker
            state.metrics.remove_worker_metrics(worker_name)

            # Purge from inspector
            self.inspector.purge_worker(worker_name)

            logger.debug("Purged offline worker: %s", worker_name)
