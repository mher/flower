from __future__ import absolute_import

import json

from tornado import web
from tornado import gen
from tornado import httpclient

from ..views import BaseHandler
from ..api.workers import ListWorkers


class WorkerView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self, name):
        refresh = self.get_argument('refresh', default=False, type=bool)

        if refresh:
            yield ListWorkers.update_workers(app=self.application, workername=name)

        worker = ListWorkers.worker_cache.get(name)

        if worker is None:
            raise web.HTTPError(404, "Unknown worker '%s'" % name)

        self.render("worker.html", worker=dict(worker, name=name))
