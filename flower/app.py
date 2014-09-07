from __future__ import absolute_import

import os
import logging

from functools import partial
from concurrent.futures import ThreadPoolExecutor

import celery
import tornado.web

from tornado import ioloop

from .api import control
from .urls import handlers
from .events import Events


logger = logging.getLogger(__name__)


class Flower(tornado.web.Application):
    pool_executor_cls = ThreadPoolExecutor
    max_workers = 4

    def __init__(self, options, celery_app=None, events=None,
                 io_loop=None, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.options = options
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        self.ssl = None
        if options and self.options.certfile and self.options.keyfile:
            cwd = os.environ.get('PWD') or os.getcwd()
            self.ssl = {
                'certfile': os.path.join(cwd, self.options.certfile),
                'keyfile': os.path.join(cwd, self.options.keyfile),
            }

        self.celery_app = celery_app or celery.Celery()
        self.events = events or Events(self.celery_app, db=options.db,
                                       persistent=options.persistent,
                                       enable_events=options.enable_events,
                                       io_loop=self.io_loop,
                                       max_tasks_in_memory=options.max_tasks)

    def start(self):
        self.pool = self.pool_executor_cls(max_workers=self.max_workers)
        self.events.start()
        self.listen(self.options.port, address=self.options.address,
                    ssl_options=self.ssl, xheaders=self.options.xheaders)
        self.io_loop.add_future(
            control.ControlHandler.update_workers(app=self),
            callback=lambda x: logger.debug('Updated workers cache'))
        self.io_loop.start()

    def stop(self):
        self.events.stop()
        self.pool.shutdown(wait=False)

    def delay(self, method, *args, **kwargs):
        return self.pool.submit(partial(method, *args, **kwargs))

    @property
    def transport(self):
        return getattr(self.celery_app.connection().transport,
                       'driver_type', None)
