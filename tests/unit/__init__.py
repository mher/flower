from unittest.mock import patch
from urllib.parse import urlencode

import tornado.testing
from tornado.options import options

from tornado.concurrent import Future

import celery

from flower.app import Flower
from flower.urls import handlers
from flower.events import Events
from flower.urls import settings
from flower import command  # noqa: F401 side effect - define options


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):

    def _get_celery_app(self):
        return celery.Celery()

    def get_app(self, capp=None):
        if not capp:
            capp = self._get_celery_app()
        events = Events(capp)
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
