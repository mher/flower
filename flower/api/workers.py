from __future__ import absolute_import

from tornado import web

from ..models import WorkersModel
from ..views import BaseHandler


class ListWorkers(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        self.write(WorkersModel.get_latest(app).workers)

class UntrackWorkers(BaseHandler):
    @web.authenticated
    def post(self, workername):
        state = self.application.state
        with state._update_lock:
            if workername in state._stats:
                del state._stats[workername]
        self.write(dict(message="Removed from the worker list successfully"))
