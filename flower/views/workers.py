from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel, WorkerModel


class WorkersView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        workers = WorkersModel.get_latest(app).workers
        broker = app.celery_app.connection().as_uri()

        self.render("workers.html", workers=workers, broker=broker)


class WorkerView(BaseHandler):
    @web.authenticated
    def get(self, workername):
        app = self.application
        worker = WorkerModel.get_worker(app, workername)
        if worker is None:
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)

        self.render("worker.html", worker=worker)
