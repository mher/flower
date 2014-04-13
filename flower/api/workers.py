from __future__ import absolute_import

from tornado import web

from ..models import WorkersModel
from ..views import BaseHandler


class ListWorkers(BaseHandler):
    @web.authenticated
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
        app = self.application
        self.write(WorkersModel.get_latest(app).workers)
