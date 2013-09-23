try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import tornado.testing

import celery

from flower.app import Flower
from flower.urls import handlers
from flower.events import Events
from flower.state import State
from flower.settings import APP_SETTINGS


class AsyncHTTPTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self, celery_app=None, events=None, state=None):
        celery_app = celery_app or celery.Celery()
        events = events or Events(celery_app)
        state = state or State(celery_app)
        self.app = Flower(celery_app=celery_app, events=events,
                          state=state, handlers=handlers, **APP_SETTINGS)
        return self.app

    def get(self, url, **kwargs):
        return self.fetch(url, **kwargs)

    def post(self, url, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs['body'] = urlencode(kwargs['body'])
        return self.fetch(url, method='POST', **kwargs)
