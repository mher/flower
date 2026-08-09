import sys
import logging
import time

from concurrent.futures import ThreadPoolExecutor
from functools import cached_property

import celery
import tornado.web

from tornado import ioloop
from tornado.httpserver import HTTPServer
from tornado.netutil import bind_sockets
from tornado.web import url

from .urls import handlers as default_handlers
from .events import Events
from .inspector import Inspector
from .options import default_options
from .utils.blocking import BlockingOperationRunner


logger = logging.getLogger(__name__)


if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy())  # pylint: disable=deprecated-class

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
        self.blocking_runner = BlockingOperationRunner(self.executor)

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

    def start_http_server(self):
        if not self.options.unix_socket:
            sockets = bind_sockets(
                self.options.port,
                address=self.options.address,
            )
            server = HTTPServer(
                self,
                ssl_options=self.ssl_options,
                xheaders=self.options.xheaders,
            )
            server.add_sockets(sockets)
            return sockets[0].getsockname()[1]

        from tornado.netutil import bind_unix_socket
        server = HTTPServer(self)
        socket = bind_unix_socket(self.options.unix_socket, mode=0o777)
        server.add_socket(socket)
        return None

    def start(self):
        self.events.start()

        self.started = True
        self.update_workers()
        self.io_loop.start()

    def stop(self):
        if self.started:
            self.events.stop()
            logging.debug("Stopping executors...")
            self.executor.shutdown(wait=False)
            logging.debug("Stopping event loop...")
            self.io_loop.stop()
            self.started = False

    @cached_property
    def broker_uri(self):
        with self.capp.connection() as conn:
            return conn.as_uri()

    @cached_property
    def broker_uri_with_password(self):
        with self.capp.connection() as conn:
            return conn.as_uri(include_password=True)

    @cached_property
    def transport(self):
        with self.capp.connection() as conn:
            return getattr(conn.transport, 'driver_type', None)

    @property
    def workers(self):
        return self.inspector.workers

    def update_workers(self, workername=None):
        return self.inspector.inspect(workername)

    def purge_offline_worker_metrics(self):
        threshold = self.options.purge_offline_workers
        if threshold is None:
            return

        state = self.events.state
        now = time.time()
        worker_names = set(state.counter) | set(state.workers) | \
            set(self.inspector.workers)
        offline_workers = set()

        for worker_name in worker_names:
            worker = state.workers.get(worker_name)
            if worker is None:
                offline_workers.add(worker_name)
                continue
            if worker.alive:
                continue
            if not worker.heartbeats or \
                    now - max(worker.heartbeats) > threshold:
                offline_workers.add(worker_name)

        if not offline_workers:
            return

        removed = state.metrics.remove_workers(offline_workers)
        if removed:
            logger.debug("Purged metrics for %d offline workers", removed)
