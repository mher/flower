import sys
import logging
from urllib.parse import quote

from concurrent.futures import ThreadPoolExecutor

import celery
import tornado.web

from tornado import ioloop
from tornado.httpserver import HTTPServer
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

        self._http_server = None
        self._executor = None

    def _start_executor(self):
        if self._executor is None:
            logging.debug("Starting executor...")
            ctx = self.pool_executor_cls(max_workers=self.max_workers)
            self._executor = ctx.__enter__()  # pylint: disable=unnecessary-dunder-call
            self.io_loop.set_default_executor(self._executor)

    def _stop_executor(self):
        if self._executor is not None:
            logging.debug("Stop executor...")
            self._executor.__exit__(None, None, None)
            self._executor = None

    def _start_events(self):
        self.events.start()

    def _stop_events(self):
        self.events.stop()

    def _start_http_server(self):
        logging.debug("Starting HTTP server...")
        if not self.options.unix_socket:
            http_server = self.listen(
                self.options.port,
                address=self.options.address,
                ssl_options=self.ssl_options,
                xheaders=self.options.xheaders
            )
        else:
            from tornado.netutil import bind_unix_socket

            http_server = HTTPServer(self)
            socket = bind_unix_socket(self.options.unix_socket, mode=0o777)
            http_server.add_socket(socket)
        self._http_server = http_server

    def _stop_http_server(self):
        logging.debug("Stopping HTTP server...")
        self.io_loop.run_sync(
            self._http_server.close_all_connections, timeout=5
        )
        self._http_server.stop()
        self._http_server = None

    def start_server(self):
        if self._http_server is not None:
            logging.debug("Flower server already started.")
            return
        logging.debug("Starting Flower server...")
        self._start_executor()
        self._start_events()
        self._start_http_server()
        logging.debug("Flower server started.")

    def stop_server(self):
        if self._http_server is None:
            logging.debug("Flower server already stopped.")
            return
        logging.debug("Stopping Flower server...")
        self._stop_events()
        self._stop_http_server()
        self._stop_executor()
        logging.debug("Flower server stopped.")

    def serve_forever(self):
        if not self._http_server:
            raise RuntimeError("The server is not running")
        logging.debug("Starting event loop...")
        self.io_loop.start()

    def shutdown(self):
        if self._http_server:
            raise RuntimeError("The server is still running")
        logging.debug("Stopping event loop...")
        self.io_loop.stop()

    @property
    def transport(self):
        return getattr(self.capp.connection().transport, 'driver_type', None)

    @property
    def workers(self):
        return self.inspector.workers

    def update_workers(self, workername=None):
        return self.inspector.inspect(workername)

    def _get_scheme(self):
        if self.options.unix_socket:
            return "http+unix"
        if self.ssl_options:
            return "https"
        return "http"

    def _get_socket(self):
        sockets = getattr(self._http_server, "_sockets", None)  # pylint: disable=protected-access
        if sockets:
            return list(sockets.values())[0]
        return None

    def _get_domain(self):
        if self.options.unix_socket:
            raise RuntimeError("UNIX socket")

        sock = self._get_socket()
        if sock is not None:
            return sock.getsockname()[0]

        return self.options.address or "0.0.0.0"

    def _get_port(self):
        if self.options.unix_socket:
            raise RuntimeError("UNIX socket")

        sock = self._get_socket()
        if sock is not None:
            return sock.getsockname()[1]

        return self.options.port

    def _get_authority(self):
        if self.options.unix_socket:
            return quote(self.options.unix_socket)

        return f"{self._get_domain()}:{self._get_port()}"

    def _get_url_path(self, path=None):
        path = path or ""
        if not self.options.url_prefix:
            return path

        prefix = self.options.url_prefix.strip("/")
        return f"/{prefix}{path}"

    def get_url(self, path=None):
        path = self._get_url_path(path)
        return f"{self._get_scheme()}://{self._get_authority()}{path}"

    #
    # For backward compatibility
    #

    def start(self):
        self.start_server()
        self.update_workers()
        self.serve_forever()

    def stop(self):
        self.stop_server()
        self.shutdown()

    @property
    def started(self):
        return self._http_server is not None

    @started.setter
    def started(self, value):
        if value:
            self.start_server()
        else:
            self.stop_server()

    @property
    def executor(self):
        return self._executor
