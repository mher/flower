from unittest.mock import patch
from urllib.parse import urlencode

import celery
import tornado.testing
from tornado.ioloop import IOLoop
from tornado.options import options

from flower import command  # noqa: F401 side effect - define options
from flower.app import Flower
from flower.events import Events
from flower.urls import handlers, settings


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):

    def _get_celery_app(self):
        return celery.Celery()

    def get_app(self, capp=None):
        if not capp:
            capp = self._get_celery_app()
        events = Events(capp, IOLoop.current())
        app = Flower(capp=capp, events=events,
                     options=options, handlers=handlers, **settings)
        return app

    def get(self, url, **kwargs):
        return self.fetch(url, **kwargs)

    def post(self, url, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs['body'] = urlencode(kwargs['body'])
        return self.fetch(url, method='POST', **kwargs)

    def mock_option(self, name, value):
        return patch.object(options.mockable(), name, value)
