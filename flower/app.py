from __future__ import absolute_import

import tornado.web
from tornado import ioloop

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers


class Flower(tornado.web.Application):
    def __init__(self, celery_app=None, events=None, state=None,
                 auth=None, io_loop=None, options={}, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.auth = auth or []
        self.options = options

        self.celery_app = celery_app or celery.Celery()
        self.events = events or Events(celery_app, io_loop=self.io_loop,
                                       max_tasks_in_memory=options.max_tasks)
        self.state = State(celery_app)

    def start(self):
        self.events.start()
        if self.options.inspect:
            self.state.start()
        self.listen(self.options.port, address=self.options.address)
        self.io_loop.start()
