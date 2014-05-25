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
            body = self.request.body
            options = json_decode(body) if body else {}
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
        result = celery.send_task(taskname, args=args,
                                  kwargs=kwargs, **options)
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
        """
List tasks

**Example request**:

.. sourcecode:: http

  GET /api/tasks HTTP/1.1
  Host: localhost:5555
  User-Agent: HTTPie/0.8.0

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 1109
  Content-Type: application/json; charset=UTF-8
  Etag: "b2478118015c8b825f7b88ce6b660e5449746c37"
  Server: TornadoServer/3.1.1

  {
      "e42ceb2d-8730-47b5-8b4d-8e0d2a1ef7c9": {
          "args": "[3, 4]",
          "client": null,
          "clock": 1079,
          "eta": null,
          "exception": null,
          "exchange": null,
          "expires": null,
          "failed": null,
          "kwargs": "{}",
          "name": "tasks.add",
          "received": 1398505411.107885,
          "result": "'7'",
          "retried": null,
          "retries": 0,
          "revoked": null,
          "routing_key": null,
          "runtime": 0.01610181899741292,
          "sent": null,
          "started": 1398505411.108985,
          "state": "SUCCESS",
          "succeeded": 1398505411.124802,
          "timestamp": 1398505411.124802,
          "traceback": null,
          "uuid": "e42ceb2d-8730-47b5-8b4d-8e0d2a1ef7c9"
      },
      "f67ea225-ae9e-42a8-90b0-5de0b24507e0": {
          "args": "[1, 2]",
          "client": null,
          "clock": 1042,
          "eta": null,
          "exception": null,
          "exchange": null,
          "expires": null,
          "failed": null,
          "kwargs": "{}",
          "name": "tasks.add",
          "received": 1398505395.327208,
          "result": "'3'",
          "retried": null,
          "retries": 0,
          "revoked": null,
          "routing_key": null,
          "runtime": 0.012884548006695695,
          "sent": null,
          "started": 1398505395.3289,
          "state": "SUCCESS",
          "succeeded": 1398505395.341089,
          "timestamp": 1398505395.341089,
          "traceback": null,
          "uuid": "f67ea225-ae9e-42a8-90b0-5de0b24507e0"
      }
  }

:query limit: maximum number of tasks
:query workername: filter task by workername
:query taskname: filter tasks by taskname
:query state: filter tasks by state
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        app = self.application
        limit = self.get_argument('limit', None)
        worker = self.get_argument('workername', None)
        type = self.get_argument('taskname', None)
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

  GET /api/task/info/91396550-c228-4111-9da4-9d88cfd5ddc6 HTTP/1.1
  Accept: */*
  Accept-Encoding: gzip, deflate, compress
  Host: localhost:5555


**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 575
  Content-Type: application/json; charset=UTF-8

  {
      "args": "[2, 2]",
      "client": null,
      "clock": 25,
      "eta": null,
      "exception": null,
      "exchange": null,
      "expires": null,
      "failed": null,
      "kwargs": "{}",
      "name": "tasks.add",
      "received": 1400806241.970742,
      "result": "'{\"result\": 4}'",
      "retried": null,
      "retries": null,
      "revoked": null,
      "routing_key": null,
      "runtime": 2.0037889280356467,
      "sent": null,
      "started": 1400806241.972624,
      "state": "SUCCESS",
      "succeeded": 1400806243.975336,
      "task-id": "91396550-c228-4111-9da4-9d88cfd5ddc6",
      "timestamp": 1400806243.975336,
      "traceback": null,
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
        response = {}
        for name in task._fields:
            if name not in ['uuid', 'worker']:
                response[name] = getattr(task, name, None)
        response['task-id'] = task.uuid
        response['worker'] = task.worker.hostname
        self.write(response)
