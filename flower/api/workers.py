from __future__ import absolute_import

import logging

from tornado.escape import json_decode
from tornado.web import RequestHandler, HTTPError

from celery.result import AsyncResult
from celery.backends.base import DisabledBackend


class ListWorkers(RequestHandler):
    def get(self):
        app = self.application
        self.write(WorkersModel.get_latest(app).workers)
