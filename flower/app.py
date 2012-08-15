import tornado.web
from tornado import ioloop

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers


class Flower(tornado.web.Application):
    def __init__(self, celery_app=None, events=None, state=None,
                       io_loop=None, **kwargs):
        kwargs.update(handlers=handlers)
        super(Flower, self).__init__(**kwargs)
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        self.celery_app = celery_app or celery.Celery()
        self.events = events or Events(celery_app, io_loop)
        self.state = State(celery_app)

    def start(self, port, inspect=True):
        self.events.start()
        if inspect:
            self.state.start()
        self.listen(port)
        self.io_loop.start()
