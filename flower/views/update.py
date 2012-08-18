from __future__ import absolute_import

import logging

from functools import partial

from tornado import websocket
from tornado.ioloop import PeriodicCallback

from ..models import WorkersModel
from ..settings import PAGE_UPDATE_INTERVAL


class UpdateWorkers(websocket.WebSocketHandler):
    listeners = []
    periodic_callback = None
    workers = None

    def open(self):
        app = self.application
        listeners = UpdateWorkers.listeners
        periodic_callback = UpdateWorkers.periodic_callback

        if not listeners:
            logging.debug('Starting a timer for dashboard updates')
            periodic_callback = periodic_callback or PeriodicCallback(
                    partial(UpdateWorkers.on_update_time, app),
                    PAGE_UPDATE_INTERVAL)
            periodic_callback.start()
        listeners.append(self)

    def on_message(self, message):
        pass

    def on_close(self):
        listeners = UpdateWorkers.listeners
        periodic_callback = UpdateWorkers.periodic_callback

        listeners.remove(self)
        if not listeners and periodic_callback:
            logging.debug('Stopping dashboard updates timer')
            periodic_callback.stop()

    @classmethod
    def on_update_time(cls, app):
        workers = WorkersModel.get_latest(app)

        if workers != cls.workers:
            logging.debug('Sending dashboard updates')
            for l in cls.listeners:
                l.write_message(workers.workers)
            cls.workers = workers
