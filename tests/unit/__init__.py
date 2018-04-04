try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import tornado.testing
from tornado.options import options

from tornado.concurrent import Future

import celery
import mock

from flower.app import Flower
from flower.urls import handlers
from flower.events import Events
from flower.urls import settings
from flower import command  # side effect - define options


def app_delay(method, *args, **kwargs):
    future = Future()
    future.set_result(method(*args, **kwargs))
    return future


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        capp = celery.Celery()
        events = Events(capp)
        app = Flower(capp=capp, events=events,
                     options=options, handlers=handlers, **settings)
        app.delay = lambda method, *args, **kwargs: app_delay(method, *args, **kwargs)
        return app

    def get(self, url, **kwargs):
        return self.fetch(url, **kwargs)

    def post(self, url, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs['body'] = urlencode(kwargs['body'])
        return self.fetch(url, method='POST', **kwargs)

    def mock_option(self, name, value):
        return mock.patch.object(options.mockable(), name, value)
