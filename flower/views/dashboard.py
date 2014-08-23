from __future__ import absolute_import

import logging

from functools import partial
from collections import OrderedDict

from tornado import web
from tornado import websocket
from tornado.ioloop import PeriodicCallback

from . import settings
from ..views import BaseHandler


logger = logging.getLogger(__name__)


class DashboardView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        events = app.events.state
        broker = app.celery_app.connection().as_uri()

        workers = {k:dict(v) for k,v in events.counter.items()}
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

    def open(self):
        if not settings.AUTO_REFRESH:
            self.write_message({})
            return

        app = self.application

        if not self.listeners:
            if self.periodic_callback is None:
                cls = DashboardUpdateHandler
                cls.periodic_callback = PeriodicCallback(
                    partial(cls.on_update_time, app),
                    settings.PAGE_UPDATE_INTERVAL)
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
            workers[name] = dict(
                status=worker.alive,
                active=worker.active,
                processed=counter.get('task-received', 0),
                failed=counter.get('task-failed', 0),
                revoked=counter.get('task-revoked', 0),
                retried=counter.get('task-retried', 0),
                loadavg=worker.loadavg)
        return workers
