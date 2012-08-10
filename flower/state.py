from __future__ import absolute_import
from __future__ import with_statement

import time
import copy
import logging
import threading

from pprint import pformat

import celery

from .settings import CELERY_INSPECT_TIMEOUT


class State(threading.Thread):
    def __init__(self, celery_app):
        threading.Thread.__init__(self)
        self.daemon = True
        self._celery_app = celery_app

        self._update_lock = threading.Lock()
        self._stats = {}
        self._registered_tasks = {}
        self._scheduled_tasks = {}
        self._active_tasks = {}
        self._reserved_tasks = {}
        self._revoked_tasks = {}
        self._ping = {}
        self._active_queues = {}
        self._confs = {}

    def run(self):
        transport = self._celery_app.connection().transport.driver_type
        if transport not in ('amqp', 'redis', 'mongodb'):
            logging.error("Dashboard and worker management commands are "
                    "not available for '%s' transport" % transport)
            return

        if celery.__version__.rsplit('.', 1)[0] < '3.1':
            logging.warning("Configuration viewer is not available for "
                "Celery versions prior to 3.1")

        timeout = CELERY_INSPECT_TIMEOUT / 1000.0
        i = self._celery_app.control.inspect(timeout=timeout)
        try_interval = 1
        while True:
            try:
                try_interval *= 2
                logging.debug('Inspecting workers')
                stats = i.stats() or {}
                logging.debug('Stats: %s' % pformat(stats))
                registered = i.registered() or {}
                scheduled = i.scheduled() or {}
                active = i.active() or {}
                reserved = i.reserved() or {}
                revoked = i.revoked() or {}
                ping = i.ping() or {}
                active_queues = i.active_queues() or {}
                # Inspect.conf was introduced in Celery 3.1
                conf = hasattr(i, 'conf') and i.conf() or {}

                with self._update_lock:
                    self._stats = stats
                    self._registered_tasks = registered
                    self._scheduled_tasks = scheduled
                    self._active_tasks = active
                    self._reserved_tasks = reserved
                    self._revoked_tasks = revoked
                    self._ping = ping
                    self._active_queues = active_queues
                    self._conf = conf

                try_interval = 1
            except (KeyboardInterrupt, SystemExit):
                import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("Failed to inspect workers: '%s', trying "
                              "again in %s seconds" % (e, try_interval))
                time.sleep(try_interval)

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

    @property
    def conf(self):
        with self._update_lock:
            return copy.deepcopy(self._conf)
