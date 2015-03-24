try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import tornado.testing
import tornado.options

import celery

from flower.app import Flower
from flower.urls import handlers
from flower.events import Events
from flower.urls import settings
from flower import command  # side effect - define options


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        capp = celery.Celery()
        events = Events(capp)
        app = Flower(capp=capp, events=events,
                     options=tornado.options.options,
                     handlers=handlers, **settings)
        app.delay = lambda method, *args, **kwargs: method(*args, **kwargs)
        return app

    def get(self, url, **kwargs):
        return self.fetch(url, **kwargs)

    def post(self, url, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs['body'] = urlencode(kwargs['body'])
        return self.fetch(url, method='POST', **kwargs)
