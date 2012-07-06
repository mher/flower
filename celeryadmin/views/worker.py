from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel, WorkerModel


class WorkersView(BaseHandler):
    def get(self):
        self.render("workers.html",
                    workers=WorkersModel.get_latest().workers)


class WorkerView(BaseHandler):
    def get(self, workername):
        worker = WorkerModel.get_worker(workername)
        if worker is None:
            raise web.HTTPError(404)

        self.render("worker.html", worker=worker)
