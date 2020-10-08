import prometheus_client

from tornado import web
from tornado import gen

from ..views import BaseHandler


class Metrics(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        self.write(prometheus_client.generate_latest())


class Healthcheck(BaseHandler):
    @gen.coroutine
    def get(self):
        self.write("OK")
