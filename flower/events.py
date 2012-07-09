from __future__ import absolute_import

import logging
import threading

import celery

from celery.events import EventReceiver
from celery.messaging import establish_connection
from celery.events.state import state
from celery.events.snapshot import Polaroid

celery = celery.current_app


class DumpCam(Polaroid):
    def __init__(self, state, freq=1.0):
        Polaroid.__init__(self, state, freq)

    def on_shutter(self, state):
        if not state.event_count:
            # No new events since last snapshot.
            return


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
                    with DumpCam(state, freq=1.0):
                        recv.capture(limit=None, timeout=None)
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("An error occurred while capturing events"
                              ": %s" % e)


tasks = state.tasks
