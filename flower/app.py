from __future__ import absolute_import

import tornado.web
from tornado import ioloop

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers


class Flower(tornado.web.Application):
    def __init__(self, celery_app=None, events=None, state=None,
                       auth=None, io_loop=None, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.io_loop = io_loop or ioloop.IOLoop.instance()
        self.auth = auth or []

        self.celery_app = celery_app or celery.Celery()
        self.events = events or Events(celery_app, io_loop)
        self.state = State(celery_app)

    def start(self, port, address='', inspect=True):
        self.events.start()
        if inspect:
            self.state.start()
        self.listen(port, address=address)
        self.io_loop.start()
