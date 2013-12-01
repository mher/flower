from __future__ import absolute_import

import logging

from functools import partial
from pprint import pformat

from tornado import websocket
from tornado.ioloop import PeriodicCallback

from . import settings
from ..models import WorkersModel


class UpdateWorkers(websocket.WebSocketHandler):
    listeners = []
    periodic_callback = None
    workers = None

    def open(self):
        if not settings.AUTO_REFRESH:
            self.write_message({})
            return

        app = self.application

        if not self.listeners:
            logging.debug('Starting a timer for dashboard updates')
            periodic_callback = self.periodic_callback or PeriodicCallback(
                partial(UpdateWorkers.on_update_time, app),
                settings.PAGE_UPDATE_INTERVAL)
            if not periodic_callback._running:
                periodic_callback.start()
        self.listeners.append(self)

    def on_message(self, message):
        pass

    def on_close(self):
        if self in self.listeners:
            self.listeners.remove(self)
        if not self.listeners and self.periodic_callback:
            logging.debug('Stopping dashboard updates timer')
            self.periodic_callback.stop()

    @classmethod
    def on_update_time(cls, app):
        workers = WorkersModel.get_latest(app)
        changes = workers.workers

        if workers != cls.workers and changes:
            logging.debug('Sending dashboard updates: %s', pformat(changes))
            for l in cls.listeners:
                l.write_message(changes)
            cls.workers = workers
