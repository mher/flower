from __future__ import absolute_import

import logging

from tornado import websocket
from tornado.ioloop import PeriodicCallback

from ..models import WorkersModel
from ..settings import PAGE_UPDATE_INTERVAL


class UpdateWorkers(websocket.WebSocketHandler):
    listeners = []
    periodic_callback = None
    workers = None

    def open(self):
        listeners = UpdateWorkers.listeners
        periodic_callback = UpdateWorkers.periodic_callback

        if not listeners:
            periodic_callback = periodic_callback or PeriodicCallback(
                    UpdateWorkers.on_update_time, PAGE_UPDATE_INTERVAL)
            periodic_callback.start()
        listeners.append(self)

    def on_message(self, message):
        logging.error(message)

    def on_close(self):
        listeners = UpdateWorkers.listeners
        periodic_callback = UpdateWorkers.periodic_callback

        listeners.remove(self)
        if not listeners and periodic_callback:
            periodic_callback.stop()

    @classmethod
    def on_update_time(cls):
        workers = WorkersModel.get_latest()

        if workers != cls.workers:
            for l in cls.listeners:
                l.write_message(workers.workers)
            cls.workers = workers
