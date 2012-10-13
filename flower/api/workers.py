from __future__ import absolute_import

from tornado import web

from ..models import WorkersModel
from ..views import BaseHandler


class ListWorkers(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        self.write(WorkersModel.get_latest(app).workers)
