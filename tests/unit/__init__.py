from unittest.mock import patch
from urllib.parse import urlencode

import celery
import tornado.testing
from tornado.options import options
from tornado.httpclient import AsyncHTTPClient, HTTPResponse

from flower import command  # noqa: F401 side effect - define options
from flower.app import Flower
from flower.urls import handlers, settings


class AsyncHTTPTestCase(tornado.testing.AsyncTestCase):

    def setUp(self) -> None:
        super().setUp()
        self._http_client = AsyncHTTPClient()
        self._capp = celery.Celery()
        self._start_flower()

    def _start_flower(self):
        self._app = Flower(
            capp=self._capp,
            io_loop=self.io_loop,
            options=options,
            handlers=handlers,
            **settings
        )
        self._app.start_server()

    def _stop_flower(self):
        self._app.stop_server()

    def _restart_flower(self, reset_celery_app=False):
        self._stop_flower()
        if reset_celery_app:
            self._capp = celery.Celery()
        self._start_flower()

    def tearDown(self) -> None:
        self._http_client.close()
        self._app.stop_server()
        del self._http_client
        del self._app
        super().tearDown()

    def fetch(
        self, path: str, raise_error: bool = False, **kwargs
    ) -> HTTPResponse:
        url = self._app.get_url(path)

        def fetch():
            return self._http_client.fetch(url, raise_error=raise_error, **kwargs)

        return self.io_loop.run_sync(
            fetch,
            timeout=tornado.testing.get_async_test_timeout(),
        )

    def get(self, url, **kwargs):
        return self.fetch(url, **kwargs)

    def post(self, url, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs['body'] = urlencode(kwargs['body'])
        return self.fetch(url, method='POST', **kwargs)

    def mock_option(self, name, value):
        return patch.object(options.mockable(), name, value)
