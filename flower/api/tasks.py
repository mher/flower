from __future__ import absolute_import

import logging

from tornado.escape import json_decode
from tornado.web import RequestHandler, HTTPError

from celery.result import AsyncResult
from celery.backends.base import DisabledBackend


class BaseTaskHandler(RequestHandler):
    def get_task_args(self):
        options = json_decode(self.request.body)
        args = options.pop('args', [])
        kwargs = options.pop('kwargs', {})
        return args, kwargs, options

    @staticmethod
    def backend_configured(result):
        return not isinstance(result.backend, DisabledBackend)


class TaskAsyncApply(BaseTaskHandler):
    def post(self, taskname):
        celery = self.application.celery_app

        args, kwargs, options = self.get_task_args()
        logging.debug("Invoking task '%s' with '%s' and '%s'" %
                            (taskname, args, kwargs))
        result = celery.send_task(taskname, args=args, kwargs=kwargs)
        response = {'task-id': result.task_id}
        if self.backend_configured(result):
            response.update(state=result.state)
        self.write(response)


class TaskResult(BaseTaskHandler):
    def get(self, taskid):
        result = AsyncResult(taskid)
        if not self.backend_configured(result):
            raise HTTPError(503)
        response = {'task-id': taskid, 'state': result.state}
        if result.ready():
            response.update({'result': result.result})
        self.write(response)
