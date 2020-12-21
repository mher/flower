import logging

from tornado import web
from tornado import gen

from ..views import BaseHandler
from ..api.workers import ListWorkers


logger = logging.getLogger(__name__)


class WorkerView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self, name):
        try:
            self.application.update_workers(workername=name)
        except Exception as e:
            logger.error(e)

        worker = self.application.workers.get(name)

        if worker is None:
            raise web.HTTPError(404, "Unknown worker '%s'" % name)
        if 'stats' not in worker:
            raise web.HTTPError(
                404,
                "Unable to get stats for '%s' worker" % name
            )

        self.render("worker.html", worker=dict(worker, name=name))
