from __future__ import absolute_import

import logging
import threading

from tornado.ioloop import PeriodicCallback

from celery.events import EventReceiver
from celery.events.state import State

from .settings import CELERY_EVENTS_ENABLE_INTERVAL


class Events(threading.Thread):
    state = State()

    def __init__(self, celery_app):
        threading.Thread.__init__(self)
        self.daemon = True
        self._celery_app = celery_app
        self._timer = PeriodicCallback(self.on_enable_events,
                                       CELERY_EVENTS_ENABLE_INTERVAL)

    def start(self):
        threading.Thread.start(self)
        self._timer.start()

    def run(self):
        while True:
            try:
                logging.info("Enabling events")
                self._celery_app.control.enable_events()

                with self._celery_app.connection() as conn:
                    recv = EventReceiver(conn,
                                handlers={"*": self.on_event})
                    recv.capture(limit=None, timeout=None)
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("An error occurred while capturing events"
                              ": %s" % e)

    def on_enable_events(self):
        # Periodically enable events for workers
        # launched after flower
        logging.debug('Enabling events')
        try:
            self._celery_app.control.enable_events()
        except Exception as e:
            logging.error("An error occurred while enabling events: %s" % e)

    def on_event(self, event):
        handler = getattr(self, 'on_' + event['type'].replace('-', '_'), None)
        if handler:
            handler(event)
        self.state.event(event)

    def on_task_succeeded(self, event):
        pass

    def on_task_failed(self, event):
        pass
