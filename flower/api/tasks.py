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
        try:
            options = json_decode(self.request.body) if self.request.body else {}
        except ValueError as e:
            raise HTTPError(400, str(e))
        args = options.pop('args', [])
        kwargs = options.pop('kwargs', {})

        if not isinstance(args, (list, tuple)):
            raise HTTPError(400, 'args must be an array')

        return args, kwargs, options

    @staticmethod
    def backend_configured(result):
        return not isinstance(result.backend, DisabledBackend)

    def write_error(self, status_code, **kwargs):
        self.set_status(status_code)

    def safe_result(self, result):
        "returns json encodable result"
        try:
            json.dumps(result)
        except TypeError:
            return repr(result)
        else:
            return result


class TaskAsyncApply(BaseTaskHandler):
    @web.authenticated
    def post(self, taskname):
        """
Execute a task

**Example request**:

.. sourcecode:: http

  POST /api/task/async-apply/tasks.add HTTP/1.1
  Accept: application/json
  Accept-Encoding: gzip, deflate, compress
  Content-Length: 16
  Content-Type: application/json; charset=utf-8
  Host: localhost:5555

  {
      "args": [1, 2]
  }

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 71
  Content-Type: application/json; charset=UTF-8
  Date: Sun, 13 Apr 2014 15:55:00 GMT

  {
      "state": "PENDING",
      "task-id": "abc300c7-2922-4069-97b6-a635cc2ac47c"
  }

:query args: a list of arguments
:query kwargs: a dictionary of arguments
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task
        """
        celery = self.application.celery_app

        args, kwargs, options = self.get_task_args()
        logging.info("Invoking a task '%s' with '%s' and '%s'",
                      taskname, args, kwargs)

        try:
            task = celery.tasks[taskname]
        except KeyError:
            raise HTTPError(404, "Unknown task '%s'" % taskname)

        result = task.apply_async(args=args, kwargs=kwargs, **options)
        response = {'task-id': result.task_id}
        if self.backend_configured(result):
            response.update(state=result.state)
        self.write(response)


class TaskSend(BaseTaskHandler):
    @web.authenticated
    def post(self, taskname):
        """
Execute a task by name (doesn't require task sources)

**Example request**:

.. sourcecode:: http

  POST /api/task/send-task/tasks.add HTTP/1.1
  Accept: application/json
  Accept-Encoding: gzip, deflate, compress
  Content-Length: 16
  Content-Type: application/json; charset=utf-8
  Host: localhost:5555

  {
      "args": [1, 2]
  }

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 71
  Content-Type: application/json; charset=UTF-8

  {
      "state": "SUCCESS",
      "task-id": "c60be250-fe52-48df-befb-ac66174076e6"
  }

:query args: a list of arguments
:query kwargs: a dictionary of arguments
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task
        """
        celery = self.application.celery_app

        args, kwargs, options = self.get_task_args()
        logging.debug("Invoking task '%s' with '%s' and '%s'",
                      taskname, args, kwargs)
        result = celery.send_task(taskname, args=args, kwargs=kwargs, **options)
        response = {'task-id': result.task_id}
        if self.backend_configured(result):
            response.update(state=result.state)
        self.write(response)


class TaskResult(BaseTaskHandler):
    @web.authenticated
    def get(self, taskid):
        """
Get a task result

**Example request**:

.. sourcecode:: http

  GET /api/task/result/c60be250-fe52-48df-befb-ac66174076e6 HTTP/1.1
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 84
  Content-Type: application/json; charset=UTF-8

  {
      "result": 3,
      "state": "SUCCESS",
      "task-id": "c60be250-fe52-48df-befb-ac66174076e6"
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 503: result backend is not configured
        """
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

        tasks = []
        for task_id, task in TaskModel.iter_tasks(
                app, limit=limit, type=type,
                worker=worker, state=state):
            task = task.as_dict()
            task.pop('worker')
            tasks.append((task_id, task))
        self.write(dict(tasks))


class TaskInfo(BaseTaskHandler):
    def get(self, taskid):
        """
Get a task info

**Example request**:

.. sourcecode:: http

  GET /api/task/info/c60be250-fe52-48df-befb-ac66174076e6 HTTP/1.1
  Accept: */*
  Accept-Encoding: gzip, deflate, compress
  Host: localhost:5555


**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 171
  Content-Type: application/json; charset=UTF-8

  {
      "args": "[1, 2]",
      "kwargs": "{}",
      "name": "tasks.add",
      "result": "'3'",
      "state": "SUCCESS",
      "task-id": "c60be250-fe52-48df-befb-ac66174076e6",
      "worker": "celery@worker1"
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task
        """

        task = TaskModel.get_task_by_id(self.application, taskid)
        if not task:
            raise HTTPError(404, "Unknown task '%s'" % taskid)

        self.write({
            'task-id': task.uuid,
            'name': getattr(task, 'name', None),
            'state': task.state,
            'args': task.args,
            'kwargs': task.kwargs,
            'result': getattr(task, 'result', None),
            'worker': task.worker.hostname,
        })
