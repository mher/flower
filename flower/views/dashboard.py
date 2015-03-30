from __future__ import absolute_import

import logging

from functools import partial
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

try:
    from urllib.parse import urlparse  # py2
except ImportError:
    from urlparse import urlparse  # py3

from tornado import web
from tornado import gen
from tornado import websocket
from tornado.ioloop import PeriodicCallback

from ..views import BaseHandler
from ..api.workers import ListWorkers


logger = logging.getLogger(__name__)


class DashboardView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        refresh = self.get_argument('refresh', default=False, type=bool)

        app = self.application
        events = app.events.state
        broker = app.capp.connection().as_uri()

        if refresh:
            yield ListWorkers.update_workers(app=app)

        workers = dict((k, dict(v)) for (k, v) in events.counter.items())
        for name, info in workers.items():
            worker = events.workers[name]
            info.update(self._as_dict(worker))
            info.update(status=worker.alive)
        self.render("dashboard.html", workers=workers, broker=broker)

    @classmethod
    def _as_dict(cls, worker):
        return dict((k, worker.__getattribute__(k)) for k in worker._fields)


class DashboardUpdateHandler(websocket.WebSocketHandler):
    listeners = []
    periodic_callback = None
    workers = None
    page_update_interval = 2000
    ws_allowed_hosts = None

    def __init__(self, *va, **kva):
        super(DashboardUpdateHandler, self).__init__(*va, **kva)
        app = self.application
        if app.options.ws_allowed_hosts is not None:
            self.ws_allowed_hosts = [ urlparse(host).netloc for host in app.options.ws_allowed_hosts ]

    def check_origin(self, origin):
        if not self.ws_allowed_hosts:
            return super(DashboardUpdateHandler, self).check_origin(origin)
        parsed_origin = urlparse(origin)
        return parsed_origin.netloc in self.ws_allowed_hosts

    def open(self):
        app = self.application
        if not app.options.auto_refresh:
            self.write_message({})
            return

        if not self.listeners:
            if self.periodic_callback is None:
                cls = DashboardUpdateHandler
                cls.periodic_callback = PeriodicCallback(
                    partial(cls.on_update_time, app),
                    self.page_update_interval)
            if not self.periodic_callback._running:
                logger.debug('Starting a timer for dashboard updates')
                self.periodic_callback.start()
        self.listeners.append(self)

    def on_message(self, message):
        pass

    def on_close(self):
        if self in self.listeners:
            self.listeners.remove(self)
        if not self.listeners and self.periodic_callback:
            logger.debug('Stopping dashboard updates timer')
            self.periodic_callback.stop()

    @classmethod
    def on_update_time(cls, app):
        update = cls.dashboard_update(app)
        if update:
            for l in cls.listeners:
                l.write_message(update)

    @classmethod
    def dashboard_update(cls, app):
        state = app.events.state
        workers = OrderedDict()

        for name, worker in sorted(state.workers.items()):
            counter = state.counter[name]
            started = counter.get('task-started', 0)
            processed = counter.get('task-received', 0)
            failed = counter.get('task-failed', 0)
            succeeded = counter.get('task-succeeded', 0)
            retried = counter.get('task-retried', 0)

            workers[name] = dict(
                status=worker.alive,
                active=started - succeeded - failed,
                processed=processed,
                failed=failed,
                succeeded=succeeded,
                retried=retried,
                loadavg=worker.loadavg)
        return workers
