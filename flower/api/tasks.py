from __future__ import absolute_import

import json
import logging

from tornado import web
from tornado.escape import json_decode
from tornado.web import HTTPError

from celery import states
from celery.result import AsyncResult
from celery.backends.base import DisabledBackend

from ..models import TaskModel
from ..views import BaseHandler


class BaseTaskHandler(BaseHandler):
    def get_task_args(self):
        options = json_decode(self.request.body)
        args = options.pop('args', [])
        kwargs = options.pop('kwargs', {})
        return args, kwargs, options

    @staticmethod
    def backend_configured(result):
        return not isinstance(result.backend, DisabledBackend)

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)


class TaskAsyncApply(BaseTaskHandler):
    @web.authenticated
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
    @web.authenticated
    def get(self, taskid):
        result = AsyncResult(taskid)
        if not self.backend_configured(result):
            raise HTTPError(503)
        response = {'task-id': taskid, 'state': result.state}
        if result.ready():
            if result.state == states.FAILURE:
                response.update({'result': self.safe_result(result.result),
                                 'traceback': result.traceback})
            else:
                response.update({'result': self.safe_result(result.result)})
        self.write(response)

    def safe_result(self, result):
        "returns json encodable result"
        try:
            json.dumps(result)
        except TypeError:
            return repr(result)
        else:
            return result



class ListTasks(BaseTaskHandler):
    @web.authenticated
    def get(self):
        app = self.application
        limit = self.get_argument('limit', None)
        worker = self.get_argument('worker', None)
        type = self.get_argument('type', None)
        state = self.get_argument('state', None)

        limit = limit and int(limit)
        worker = worker if worker != 'All' else None
        type = type if type != 'All' else None
        state = state if state != 'All' else None

        tasks = {}
        for (id, task) in TaskModel.iter_tasks(app, limit=limit, type=type,
                                               worker=worker, state=state):
            tasks[id] = task

        self.write(tasks)
