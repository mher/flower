from __future__ import absolute_import
from __future__ import with_statement

import logging
import threading

from celery import current_app as celery

from celery.events import EventReceiver
from celery.messaging import establish_connection
from celery.events.state import state


class EventCollector(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        logging.info("Enabling events")
        celery.control.enable_events()

        while True:
            try:
                with establish_connection() as connection:
                    recv = EventReceiver(
                                connection, handlers={"*": state.event})
                    recv.capture(limit=None, timeout=None)
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("An error occurred while capturing events"
                              ": %s" % e)


tasks = state.tasks
