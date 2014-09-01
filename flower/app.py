from __future__ import absolute_import

import os
import logging

from functools import partial
from concurrent.futures import ThreadPoolExecutor

import tornado.web
from tornado import ioloop

import celery

from flower.events import Events
from flower.urls import handlers
from flower.api import control


logger = logging.getLogger(__name__)


class Flower(tornado.web.Application):
    pool_executor_cls = ThreadPoolExecutor
    max_workers = 4

    def __init__(self, celery_app=None, events=None,
                 io_loop=None, options=None, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.options = options or {}
        self.auth = getattr(self.options, 'auth', [])
        self.basic_auth = getattr(self.options, 'basic_auth', None)
        self.broker_api = getattr(self.options, 'broker_api', None)
        self.format_task = getattr(self.options, 'format_task', None)
        self.natural_time = getattr(self.options, 'natural_time', None)
        self.ssl = None
        if options and self.options.certfile and self.options.keyfile:
            cwd = os.environ.get('PWD') or os.getcwd()
            self.ssl = {
                'certfile': os.path.join(cwd, self.options.certfile),
                'keyfile': os.path.join(cwd, self.options.keyfile),
            }

        self.celery_app = celery_app or celery.Celery()
        db = options.db if options else None
        persistent = options.persistent if options else None
        max_tasks = options.max_tasks if options else None
        enable_events = options.enable_events if options else None
        self.events = events or Events(celery_app, db=db,
                                       persistent=persistent,
                                       enable_events=enable_events,
                                       io_loop=self.io_loop,
                                       max_tasks_in_memory=max_tasks)

    def start(self):
        self._pool = self.pool_executor_cls(max_workers=self.max_workers)
        self.events.start()
        self.listen(self.options.port, address=self.options.address,
                    ssl_options=self.ssl, xheaders=self.options.xheaders)
        self.io_loop.add_future(
                control.ControlHandler.update_workers(app=self),
                callback=lambda x: logger.debug('Updated workers cache'))
        self.io_loop.start()

    def stop(self):
        self.events.stop()
        self._pool.shutdown(wait=False)

    def delay(self, method, *args, **kwargs):
        return self._pool.submit(partial(method, *args, **kwargs))

    @property
    def transport(self):
        try:
            return self.celery_app.connection().transport.driver_type
        except AttributeError:
            # Celery versions prior to 3 don't have driver_type
            return None
