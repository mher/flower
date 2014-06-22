from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel


class DashboardView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        workers = WorkersModel.get_latest(app).workers
        broker = app.celery_app.connection().as_uri()

        self.render("dashboard.html", workers=workers, broker=broker)
