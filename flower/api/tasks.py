import json
import logging
from collections import OrderedDict
from datetime import datetime

from celery import states
from celery.backends.base import DisabledBackend
from celery.contrib.abortable import AbortableAsyncResult
from celery.result import AsyncResult
from tornado import web
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.web import HTTPError

try:
    from flower.api.elasticsearch_history import AlternativeBackendError
except ImportError:
    AlternativeBackendError = None

try:
    from flower.api.elasticsearch_history import list_tasks_elastic_search
except ImportError:
    list_tasks_elastic_search = None

from ..utils import tasks
from ..utils.broker import Broker
from . import BaseApiHandler

logger = logging.getLogger(__name__)


class BaseTaskHandler(BaseApiHandler):
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

    def get_task_args(self):
        try:
            body = self.request.body
            options = json_decode(body) if body else {}
        except ValueError as e:
            raise HTTPError(400, str(e)) from e

        if not isinstance(options, dict):
            raise HTTPError(400, 'invalid options')

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

    def update_response_result(self, response, result):
        if result.state == states.FAILURE:
            response.update({'result': self.safe_result(result.result),
                             'traceback': result.traceback})
        else:
            response.update({'result': self.safe_result(result.result)})

    def normalize_options(self, options):
        if 'eta' in options:
            options['eta'] = datetime.strptime(options['eta'],
                                               self.DATE_FORMAT)
        if 'countdown' in options:
            options['countdown'] = float(options['countdown'])
        if 'expires' in options:
            expires = options['expires']
            try:
                expires = float(expires)
            except ValueError:
                expires = datetime.strptime(expires, self.DATE_FORMAT)
            options['expires'] = expires

    def safe_result(self, result):
        "returns json encodable result"
        try:
            json.dumps(result)
        except TypeError:
            return repr(result)
        return result


class TaskApply(BaseTaskHandler):
    @web.authenticated
    async def post(self, taskname):
        """
Execute a task by name and wait results

**Example request**:

.. sourcecode:: http

  POST /api/task/apply/tasks.add HTTP/1.1
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
      "task-id": "c60be250-fe52-48df-befb-ac66174076e6",
      "result": 3
  }

:query args: a list of arguments
:query kwargs: a dictionary of arguments
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task
        """
        args, kwargs, options = self.get_task_args()
        logger.debug("Invoking a task '%s' with '%s' and '%s'",
                     taskname, args, kwargs)

        try:
            task = self.capp.tasks[taskname]
        except KeyError as exc:
            raise HTTPError(404, f"Unknown task '{taskname}'") from exc

        try:
            self.normalize_options(options)
        except ValueError as exc:
            raise HTTPError(400, 'Invalid option') from exc

        result = task.apply_async(args=args, kwargs=kwargs, **options)
        response = {'task-id': result.task_id}

        response = await IOLoop.current().run_in_executor(
            None, self.wait_results, result, response)
        self.write(response)

    def wait_results(self, result, response):
        # Wait until task finished and do not raise anything
        result.get(propagate=False)
        # Write results and finish async function
        self.update_response_result(response, result)
        if self.backend_configured(result):
            response.update(state=result.state)
        return response


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
:query options: a dictionary of `apply_async` keyword arguments
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task
        """
        args, kwargs, options = self.get_task_args()
        logger.debug("Invoking a task '%s' with '%s' and '%s'",
                     taskname, args, kwargs)

        try:
            task = self.capp.tasks[taskname]
        except KeyError as exc:
            raise HTTPError(404, f"Unknown task '{taskname}'") from exc

        try:
            self.normalize_options(options)
        except ValueError as exc:
            raise HTTPError(400, 'Invalid option') from exc

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
        args, kwargs, options = self.get_task_args()
        logger.debug("Invoking task '%s' with '%s' and '%s'",
                     taskname, args, kwargs)
        result = self.capp.send_task(
            taskname, args=args, kwargs=kwargs, **options)
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

:query timeout: how long to wait, in seconds, before the operation times out
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 503: result backend is not configured
        """
        timeout = self.get_argument('timeout', None)
        timeout = float(timeout) if timeout is not None else None

        result = AsyncResult(taskid)
        if not self.backend_configured(result):
            raise HTTPError(503)
        response = {'task-id': taskid, 'state': result.state}

        if timeout:
            result.get(timeout=timeout, propagate=False)
            self.update_response_result(response, result)
        elif result.ready():
            self.update_response_result(response, result)
        self.write(response)


class TaskAbort(BaseTaskHandler):
    @web.authenticated
    def post(self, taskid):
        """
Abort a running task

**Example request**:

.. sourcecode:: http

  POST /api/task/abort/c60be250-fe52-48df-befb-ac66174076e6 HTTP/1.1
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 61
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Aborted '1480b55c-b8b2-462c-985e-24af3e9158f9'"
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 503: result backend is not configured
        """
        logger.info("Aborting task '%s'", taskid)

        result = AbortableAsyncResult(taskid)
        if not self.backend_configured(result):
            raise HTTPError(503)

        result.abort()

        self.write(dict(message=f"Aborted '{taskid}'"))


class GetQueueLengths(BaseTaskHandler):
    @web.authenticated
    async def get(self):
        """
Return length of all active queues

**Example request**:

.. sourcecode:: http

  GET /api/queues/length
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 94
  Content-Type: application/json; charset=UTF-8

  {
      "active_queues": [
          {"name": "celery", "messages": 0},
          {"name": "video-queue", "messages": 5}
      ]
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 503: result backend is not configured
        """
        app = self.application

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        broker = Broker(app.capp.connection().as_uri(include_password=True),
                        http_api=http_api, broker_options=self.capp.conf.broker_transport_options,
                        broker_use_ssl=self.capp.conf.broker_use_ssl)

        queues = await broker.queues(self.get_active_queue_names())
        self.write({'active_queues': queues})


class ListTasks(BaseTaskHandler):
    # pylint: disable=too-many-locals
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
          "uuid": "e42ceb2d-8730-47b5-8b4d-8e0d2a1ef7c9",
          "worker": "celery@worker1"
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
          "uuid": "f67ea225-ae9e-42a8-90b0-5de0b24507e0",
          "worker": "celery@worker1"
      }
  }

:query limit: maximum number of tasks
:query offset: skip first n tasks
:query sort_by: sort tasks by attribute (name, state, received, started)
:query workername: filter task by workername
:query taskname: filter tasks by taskname
:query state: filter tasks by state
:query received_start: filter tasks by received date (must be greater than) format %Y-%m-%d %H:%M
:query received_end: filter tasks by received date (must be less than) format %Y-%m-%d %H:%M
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        use_es = self.application.options.elasticsearch

        app = self.application
        limit = self.get_argument('limit', None)
        offset = self.get_argument('offset', default=0, type=int)
        worker = self.get_argument('workername', None)
        type = self.get_argument('taskname', None)
        state = self.get_argument('state', None)
        use_es = self.get_argument('es', use_es)
        received_start = self.get_argument('received_start', None)
        received_end = self.get_argument('received_end', None)
        sort_by = self.get_argument('sort_by', None)
        search = self.get_argument('search', None)
        started_start = self.get_argument('started_start', None)
        started_end = self.get_argument('started_end', None)
        root_id = self.get_argument('root_id', None)
        parent_id = self.get_argument('parent_id', None)

        limit = limit and int(limit)
        offset = max(offset, 0)
        worker = worker if worker != 'All' else None
        type = type if type != 'All' else None
        state = state if state != 'All' else None
        result = []

        if use_es:
            try:
                result = list_tasks_elastic_search(self)
            except AlternativeBackendError:
                use_es = False
        if not use_es:
            for task_id, task in tasks.iter_tasks(
                    app.events, limit=limit, offset=offset, sort_by=sort_by, type=type,
                    worker=worker, state=state,
                    received_start=received_start,
                    received_end=received_end,
                    search=search,
                    started_start=started_start, started_end=started_end,
                    root_id=root_id, parent_id=parent_id
            ):
                task = tasks.as_dict(task)
                worker = task.pop('worker', None)
                if worker is not None:
                    task['worker'] = worker.hostname
                result.append((task_id, task))
        self.write(OrderedDict(result))


class ListTaskTypes(BaseTaskHandler):
    @web.authenticated
    def get(self):
        """
List (seen) task types

**Example request**:

.. sourcecode:: http

  GET /api/task/types HTTP/1.1
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 44
  Content-Type: application/json; charset=UTF-8

  {
      "task-types": [
          "tasks.add",
          "tasks.sleep"
      ]
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        seen_task_types = self.application.events.state.task_types()

        response = {}
        response['task-types'] = seen_task_types
        self.write(response)


class TaskInfo(BaseTaskHandler):
    @web.authenticated
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
      "result": "'4'",
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

        task = tasks.get_task_by_id(self.application.events, taskid)
        if not task:
            raise HTTPError(404, f"Unknown task '{taskid}'")

        response = task.as_dict()
        if task.worker is not None:
            response['worker'] = task.worker.hostname

        self.write(response)
