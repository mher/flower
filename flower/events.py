from __future__ import absolute_import

import logging
import threading

from celery.events import EventReceiver
from celery.messaging import establish_connection
from celery.events.state import State



class Events(threading.Thread):
    state = State()
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Events, cls).__new__(
                    cls, *args, **kwargs)
        return cls._instance

    def __init__(self, celery_app):
        threading.Thread.__init__(self)
        self.daemon = True
        self._celery_app = celery_app

    def run(self):
        logging.info("Enabling events")
        self._celery_app.control.enable_events()

        while True:
            try:
                with establish_connection() as connection:
                    recv = EventReceiver(
                            connection, handlers={"*": self.on_event})
                    recv.capture(limit=None, timeout=None)
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("An error occurred while capturing events"
                              ": %s" % e)

    def on_event(self, event):
        handler = getattr(self, 'on_' + event['type'].replace('-', '_'), None)
        if handler:
            handler(event)
        self.state.event(event)

    def on_task_succeeded(self, event):
        pass
