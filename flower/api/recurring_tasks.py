import logging
from tornado import web

from ..utils.recurring_tasks import get_recurring_tasks
from . import BaseApiHandler

logger = logging.getLogger(__name__)


class ListRecurringTasks(BaseApiHandler):
    @web.authenticated
    def get(self):
        """
List registered Celery Beat recurring tasks

**Example request**:

.. sourcecode:: http

  GET /api/recurring-tasks HTTP/1.1
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Type: application/json; charset=UTF-8

  {
      "recurring_tasks": [
          {
              "name": "daily-report",
              "task": "tasks.generate_daily_report",
              "schedule": "<crontab: 0 0 * * * (m/h/dM/MY/d)>",
              "schedule_raw": "<crontab: 0 0 * * * (m/h/dM/MY/d)>",
              "args": [],
              "kwargs": {},
              "options": {},
              "relative": false,
              "total_run_count": null,
              "last_run_at": null,
              "last_execution": {
                  "uuid": "4f553316-c9ea-474c-ba7f-7dc9f11ca848",
                  "state": "SUCCESS",
                  "received": 1711800000.0,
                  "started": 1711800000.1,
                  "succeeded": 1711800002.5,
                  "failed": null,
                  "runtime": 2.4,
                  "result": "OK"
              }
          }
      ]
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        recurring_tasks = get_recurring_tasks(self.capp, events=self.application.events)
        self.write({'recurring_tasks': recurring_tasks, 'schedules': recurring_tasks})
