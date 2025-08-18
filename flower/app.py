import sys
import logging

from concurrent.futures import ThreadPoolExecutor

import celery
import tornado.web

from tornado import ioloop
from tornado.httpserver import HTTPServer
from tornado.ioloop import PeriodicCallback, IOLoop
from tornado.web import url

from .urls import handlers as default_handlers
from .events import Events, get_prometheus_metrics
from .inspector import Inspector
from .options import default_options
from .utils.broker import get_active_queue_lengths

logger = logging.getLogger(__name__)
# TODO: does this need to be configuration from options?
BROKER_METRICS_UPDATE_INTERVAL_SECONDS = 10
# Main dashboard view is updated regardless of this, because it subscribes to live events from celery.
WORKER_DETAILS_UPDATE_INTERVAL = 120

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
        self.io_loop.spawn_callback(self.update_broker_metrics)
        # otherwise self.workers are only updated on UI events and metrics get outdated after some time
        self.io_loop.spawn_callback(self.update_worker_details)
        self.io_loop.start()

    def stop(self):
        if self.started:
            self.events.stop()
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

    async def update_broker_metrics(self):
        logger.debug("Updating broker metrics.")

        def is_worker_alive(worker_name):
            worker = self.events.state.workers.data.get(worker_name)
            if not worker:
                return None
            return worker.alive
        while True:
            next_call = tornado.gen.sleep(BROKER_METRICS_UPDATE_INTERVAL_SECONDS)
            try:
                active_queues = await get_active_queue_lengths(self)
                metrics = get_prometheus_metrics()
                # clear old data to not leave metrics for queues no longer active
                metrics.queue_online_workers.clear()
                metrics.queue_length.clear()
                for queue_entry in active_queues:
                    queue = queue_entry["name"]
                    metrics.queue_length.labels(queue).set(queue_entry["messages"])
                    nr_of_workers = sum(
                        1 for name, data in self.workers.items() if
                        is_worker_alive(name) and any(q["name"] == queue for q in data.get("active_queues", []))
                    )
                    metrics.queue_online_workers.labels(queue).set(nr_of_workers)
            except Exception as e:
                logger.warning("Updating broker metrics failed with %s", repr(e))
            else:
                logger.debug("Done updating metrics.")
            await next_call

    async def update_worker_details(self):
        while True:
            next_call = tornado.gen.sleep(WORKER_DETAILS_UPDATE_INTERVAL)
            try:
                self.update_workers()
            except Exception as e:
                logger.warning("Failed to update workers list from celery %s", repr(e))
            await next_call
