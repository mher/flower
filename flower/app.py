from __future__ import absolute_import

import os

import tornado.web
from tornado import ioloop

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers


class Flower(tornado.web.Application):
    def __init__(self, celery_app=None, events=None, state=None,
                 io_loop=None, options=None, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.options = options or {}
        self.auth = getattr(self.options, 'auth', [])
        self.basic_auth = getattr(self.options, 'basic_auth', None)
        self.broker_api = getattr(self.options, 'broker_api', None)
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
        self.events = events or Events(celery_app, db=db,
                                       persistent=persistent,
                                       io_loop=self.io_loop,
                                       max_tasks_in_memory=max_tasks)
        self.state = State(celery_app, self.broker_api)

    def start(self):
        self.events.start()
        if self.options.inspect:
            self.state.start()
        self.listen(self.options.port, address=self.options.address,
                    ssl_options=self.ssl, xheaders=self.options.xheaders)
        self.io_loop.start()

    def stop(self):
        self.events.stop()
