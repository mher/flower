from __future__ import absolute_import
from __future__ import with_statement

import time
import shelve
import logging
import threading

from functools import partial

import celery

from tornado.ioloop import PeriodicCallback
from tornado.ioloop import IOLoop

from celery.events import EventReceiver
from celery.events.state import State

from . import api
from .settings import CELERY_EVENTS_ENABLE_INTERVAL


class EventsState(State):
    # EventsState object is created and accessed only from ioloop thread

    def __init__(self, *args, **kwargs):
        super(EventsState, self).__init__(*args, **kwargs)

    def event(self, event):
        # Send event to api subscribers (via websockets)
        classname = api.events.getClassName(event['type'])
        cls = getattr(api.events, classname, None)
        if cls:
            cls.send_message(event)

        # Save the event
        super(EventsState, self).event(event)


class Events(threading.Thread):

    def __init__(self, celery_app, db=None, persistent=False,
                 io_loop=None, **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True

        self._io_loop = io_loop or IOLoop.instance()
        self._celery_app = celery_app
        self._db = db
        self._persistent = persistent
        self.state = None

        if self._persistent and celery.__version__ < '3.0.15':
            logging.warning('Persistent mode is available with '
                            'Celery 3.0.15 and later')
            self._persistent = False

        if self._persistent:
            logging.debug("Loading state from '%s'...", db)
            state = shelve.open(self._db)
            if state:
                self.state = state['events']
            state.close()

        if not self.state:
            self.state = EventsState(**kwargs)

        self._timer = PeriodicCallback(self.on_enable_events,
                                       CELERY_EVENTS_ENABLE_INTERVAL)

    def start(self):
        threading.Thread.start(self)
        # Celery versions prior to 3 don't support enable_events
        if celery.VERSION[0] > 2:
            self._timer.start()

    def stop(self):
        if self._persistent:
            logging.debug("Saving state to '%s'...", self._db)
            state = shelve.open(self._db)
            state['events'] = self.state
            state.close()

    def run(self):
        try_interval = 1
        while True:
            try:
                try_interval *= 2

                with self._celery_app.connection() as conn:
                    recv = EventReceiver(conn,
                                         handlers={"*": self.on_event},
                                         app=self._celery_app)
                    recv.capture(limit=None, timeout=None)

                try_interval = 1
            except (KeyboardInterrupt, SystemExit):
                try:
                    import _thread as thread
                except ImportError:
                    import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("Failed to capture events: '%s', "
                              "trying again in %s seconds.",
                              e, try_interval)
                logging.debug(e, exc_info=True)
                time.sleep(try_interval)

    def on_enable_events(self):
        # Periodically enable events for workers
        # launched after flower
        logging.debug('Enabling events')
        try:
            self._celery_app.control.enable_events()
        except Exception as e:
            logging.debug("Failed to enable events: '%s'", e)

    def on_event(self, event):
        # Call EventsState.event in ioloop thread to avoid synchronization
        self._io_loop.add_callback(partial(self.state.event, event))
