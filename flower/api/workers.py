from __future__ import absolute_import

from tornado import web
from tornado import gen

from .control import ControlHandler


class ListWorkers(ControlHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        """
List workers

**Example request**:

.. sourcecode:: http

  GET /api/workers HTTP/1.1
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 119
  Content-Type: application/json; charset=UTF-8

  {
      "celery@worker1": {
          "completed_tasks": 0,
          "concurrency": 4,
          "queues": [
              "celery"
          ],
          "running_tasks": 0,
          "status": true
      },
      "celery@worker2": {
          "completed_tasks": 0,
          "concurrency": 4,
          "queues": [],
          "running_tasks": 0,
          "status": false
      }
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        refresh = self.get_argument('refresh', default=False, type=bool)
        workername = self.get_argument('workername', default=None)
        if self.worker_cache and not refresh and workername in self.worker_cache:
            self.write({workername:self.worker_cache[workername]})
            return

        yield self.update_cache(workername=workername)

        if workername and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)

        if workername:
            self.write({workername:self.worker_cache[workername]})
        else:
            self.write(self.worker_cache)
