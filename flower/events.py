from __future__ import absolute_import

import logging
import threading

from functools import partial

from tornado.ioloop import PeriodicCallback
from tornado.ioloop import IOLoop

from celery.events import EventReceiver
from celery.events.state import State

from . import api
from .settings import CELERY_EVENTS_ENABLE_INTERVAL


class EventsState(State):
    # EventState object is created and accessed only in ioloop thread
    def event(self, event):
        # Send event to api subscribers (via websockets)
        classname = api.events.getClassName(event['type'])
        cls = getattr(api.events, classname, None)
        if cls:
            cls.send_message(event)

        # Save event
        super(EventsState, self).event(event)


class Events(threading.Thread):

    def __init__(self, celery_app, io_loop=None):
        threading.Thread.__init__(self)
        self.daemon = True

        self._io_loop = io_loop or IOLoop.instance()
        self._celery_app = celery_app
        self.state = EventsState()
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
        # Call EventsState.event in ioloop thread to avoid synchronization
        self._io_loop.add_callback(partial(self.state.event, event))
