from __future__ import absolute_import
from __future__ import with_statement

import time
import copy
import logging
import threading

from pprint import pformat

import celery

from . import settings
from .utils.broker import Broker


class State(threading.Thread):

    def __init__(self, celery_app, broker_api=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self._celery_app = celery_app
        self._broker_api = broker_api

        self._update_lock = threading.Lock()
        self._inspect = threading.Event()
        self._inspect.set()
        self._last_access = time.time()

        self._stats = {}
        self._registered_tasks = {}
        self._scheduled_tasks = {}
        self._active_tasks = {}
        self._reserved_tasks = {}
        self._revoked_tasks = {}
        self._ping = {}
        self._active_queues = {}
        self._confs = {}
        self._broker_queues = []

    def run(self):
        try:
            transport = self._celery_app.connection().transport.driver_type
        except AttributeError:
            # Celery versions prior to 3 don't have driver_type
            transport = None
        if transport and transport not in ('amqp', 'redis', 'mongodb'):
            logging.error("Dashboard and worker management commands are "
                          "not available for '%s' transport", transport)
            return

        if celery.__version__ < '3.0.0':
            logging.warning("Configuration viewer is not available for "
                            "Celery versions prior to 3.0")

        timeout = settings.CELERY_INSPECT_TIMEOUT / 1000.0
        i = self._celery_app.control.inspect(timeout=timeout)

        burl = self._celery_app.connection().as_uri(include_password=True)
        broker = None
        try:
            if transport == 'amqp' and self._broker_api:
                broker = Broker(burl, self._broker_api)
                broker.queues([])
            elif transport == 'redis':
                broker = Broker(burl)
        except Exception as e:
            logging.error("Unable to get broker info: %s" % e)

        if transport == 'amqp' and not self._broker_api:
            logging.warning("Broker info is not available if --broker_api "
                            "option is not configured. Also make sure "
                            "RabbitMQ Management Plugin is enabled ("
                            "rabbitmq-plugins enable rabbitmq_management)")

        try_interval = 1
        while True:
            try:
                try_interval *= 2
                logging.debug('Inspecting workers...')
                stats = i.stats()
                logging.debug('Stats: %s', pformat(stats))
                registered = i.registered()
                logging.debug('Registered: %s', pformat(registered))
                scheduled = i.scheduled()
                logging.debug('Scheduled: %s', pformat(scheduled))
                active = i.active()
                logging.debug('Active: %s', pformat(active))
                reserved = i.reserved()
                logging.debug('Reserved: %s', pformat(reserved))
                revoked = i.revoked()
                logging.debug('Revoked: %s', pformat(revoked))
                ping = i.ping()
                logging.debug('Ping: %s', pformat(ping))
                active_queues = i.active_queues()
                logging.debug('Active queues: %s', pformat(active_queues))
                # Inspect.conf was introduced in Celery 3.1
                conf = hasattr(i, 'conf') and i.conf()
                logging.debug('Conf: %s', pformat(conf))

                try:
                    if broker:
                        broker_queues = broker.queues(self.active_queue_names)
                    else:
                        broker_queues = None
                    logging.debug('Broker queues: %s', pformat(broker_queues))
                except Exception as e:
                    broker_queues = []
                    logging.error("Failed to inspect the broker: %s", e)
                    logging.debug(e, exc_info=True)

                with self._update_lock:
                    self._stats.update(stats or {})
                    self._registered_tasks = registered or {}
                    self._scheduled_tasks = scheduled or {}
                    self._active_tasks = active or {}
                    self._reserved_tasks = reserved or {}
                    self._revoked_tasks = revoked or {}
                    self._ping = ping or {}
                    self._active_queues = active_queues or {}
                    self._conf = conf or {}
                    self._broker_queues = broker_queues or []

                try_interval = 1

                if time.time() - self._last_access > 60 * timeout:
                    self.pause()

                self._inspect.wait()

            except (KeyboardInterrupt, SystemExit):
                try:
                    import _thread as thread
                except ImportError:
                    import thread
                thread.interrupt_main()
            except Exception as e:
                logging.error("Failed to inspect workers: '%s', trying "
                              "again in %s seconds", e, try_interval)
                logging.debug(e, exc_info=True)
                time.sleep(try_interval)

    def pause(self):
        "stop inspecting workers until resume is called"
        logging.debug('Stopping inspecting workers...')
        self._inspect.clear()

    def resume(self):
        "resume inspecting workers"
        logging.debug('Resuming inspecting workers...')
        self._inspect.set()
        self._last_access = time.time()

    def __getattr__(self, name):
        if name in ['stats', 'registered_tasks', 'scheduled_tasks',
                    'active_tasks', 'reserved_tasks', 'revoked_tasks',
                    'ping', 'active_queues', 'conf', 'broker_queues']:
            with self._update_lock:
                self._last_access = time.time()
                return copy.deepcopy(getattr(self, '_' + name))
        super(State, self).__getattr__(name)

    @property
    def active_queue_names(self):
        queues = set([])
        for q in self._active_queues.values():
            queues.update(map(lambda x: x['name'], q))
        return queues
