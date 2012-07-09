from __future__ import absolute_import
from __future__ import with_statement

import time
import copy
import logging
import threading

import celery

from .settings import CELERY_INSPECT_INTERVAL


class State(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True

        self._update_lock = threading.Lock()
        self._stats = {}
        self._registered_tasks = {}
        self._scheduled_tasks = {}
        self._active_tasks = {}
        self._reserved_tasks = {}
        self._revoked_tasks = {}
        self._ping = {}
        self._active_queues = {}

    def run(self):
        i = celery.current_app.control.inspect()
        while True:
            try:
                stats = i.stats() or {}
                registered = i.registered() or {}
                scheduled = i.scheduled() or {}
                active = i.active() or {}
                reserved = i.reserved() or {}
                revoked = i.revoked() or {}
                ping = i.ping() or {}
                active_queues = i.active_queues() or {}

                with self._update_lock:
                    self._stats = stats
                    self._registered_tasks = registered
                    self._scheduled_tasks = scheduled
                    self._active_tasks = active
                    self._reserved_tasks = reserved
                    self._revoked_tasks = revoked
                    self._ping = ping
                    self._active_queues = active_queues

                time.sleep(CELERY_INSPECT_INTERVAL / 1000)
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("An error occurred while inspecting workers"
                              ": %s" % e)


    @property
    def stats(self):
        with self._update_lock:
            return copy.deepcopy(self._stats)

    @property
    def registered_tasks(self):
        with self._update_lock:
            return copy.deepcopy(self._registered_tasks)

    @property
    def scheduled_tasks(self):
        with self._update_lock:
            return copy.deepcopy(self._scheduled_tasks)

    @property
    def active_tasks(self):
        with self._update_lock:
            return copy.deepcopy(self._active_tasks)

    @property
    def reserved_tasks(self):
        with self._update_lock:
            return copy.deepcopy(self._reserved_tasks)

    @property
    def revoked_tasks(self):
        with self._update_lock:
            return copy.deepcopy(self._revoked_tasks)

    @property
    def ping(self):
        with self._update_lock:
            return copy.deepcopy(self._ping)

    @property
    def active_queues(self):
        with self._update_lock:
            return copy.deepcopy(self._active_queues)


state = State()
