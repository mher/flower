from __future__ import absolute_import

from tornado.web import RequestHandler

from ..models import WorkersModel


class ListWorkers(RequestHandler):
    def get(self):
        app = self.application
        self.write(WorkersModel.get_latest(app).workers)
