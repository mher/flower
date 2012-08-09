from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel, WorkerModel


class WorkersView(BaseHandler):
    def get(self):
        app = self.application
        self.render("workers.html",
                workers=WorkersModel.get_latest(app).workers)


class WorkerView(BaseHandler):
    def get(self, workername):
        app = self.application
        worker = WorkerModel.get_worker(app, workername)
        if worker is None:
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)

        self.render("worker.html", worker=worker)
