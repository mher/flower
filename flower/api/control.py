from __future__ import absolute_import

import logging

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel


class ControlHandler(BaseHandler):
    def is_worker(self, name):
        return WorkersModel.is_worker(self.application, name)

    def error_reason(self, workername, response):
        "extracts error message from response"
        for r in response:
            try:
                return r[workername].get('error', 'Unknown error')
            except KeyError:
                pass


class WorkerShutDown(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Shut down a worker

**Example request**:

.. sourcecode:: http

  POST /api/worker/shutdown/celery@worker2 HTTP/1.1
  Content-Length: 0
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 29
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Shutting down!"
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown worker
        """
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        logging.info("Shutting down '%s' worker", workername)
        celery.control.broadcast('shutdown', destination=[workername])
        self.write(dict(message="Shutting down!"))


class WorkerPoolRestart(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Restart worker's pool

**Example request**:

.. sourcecode:: http

  POST /api/worker/pool/restart/celery@worker2 HTTP/1.1
  Content-Length: 0
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 56
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Restarting 'celery@worker2' worker's pool"
  }

:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: pool restart is not enabled (see CELERYD_POOL_RESTARTS)
:statuscode 404: unknown worker
        """
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        logging.info("Restarting '%s' worker's pool", workername)
        response = celery.control.broadcast('pool_restart',
                                            arguments={'reload': False},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(
                message="Restarting '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to restart the '%s' pool: %s" % (
                workername, self.error_reason(workername, response)
            ))


class WorkerPoolGrow(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Grow worker's pool

**Example request**:

.. sourcecode:: http

  POST /api/worker/pool/grow/celery@worker2?n=3 HTTP/1.1
  Content-Length: 0
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 58
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Growing 'celery@worker2' worker's pool by 3"
  }

:query n: number of pool processes to grow, default is 1
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: failed to grow
:statuscode 404: unknown worker
        """

        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        n = self.get_argument('n', default=1, type=int)

        logging.info("Growing '%s' worker's pool by '%s'", workername, n)
        response = celery.control.broadcast('pool_grow',
                                            arguments={'n': n},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(
                message="Growing '%s' worker's pool by %s" % (workername, n)))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to grow '%s' worker's pool" % (
                workername, self.error_reason(workername, response)))


class WorkerPoolShrink(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Shrink worker's pool

**Example request**:

.. sourcecode:: http

  POST /api/worker/pool/shrink/celery@worker2 HTTP/1.1
  Content-Length: 0
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 60
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Shrinking 'celery@worker2' worker's pool by 1"
  }

:query n: number of pool processes to shrink, default is 1
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: failed to shrink
:statuscode 404: unknown worker
        """

        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        n = self.get_argument('n', default=1, type=int)

        logging.info("Shrinking '%s' worker's pool by '%s'", workername, n)
        response = celery.control.broadcast('pool_shrink',
                                            arguments={'n': n},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(message="Shrinking '%s' worker's pool by %s" % (
                            workername, n)))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to shrink '%s' worker's pool: %s" % (
                workername, self.error_reason(workername, response)
            ))


class WorkerPoolAutoscale(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Autoscale worker pool

**Example request**:

.. sourcecode:: http

  POST /api/worker/pool/autoscale/celery@worker2?min=3&max=10 HTTP/1.1
  Content-Length: 0
  Content-Type: application/x-www-form-urlencoded; charset=utf-8
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 66
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Autoscaling 'celery@worker2' worker (min=3, max=10)"
  }

:query min: minimum number of pool processes
:query max: maximum number of pool processes
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: autoscaling is not enabled (see CELERYD_AUTOSCALER)
:statuscode 404: unknown worker
        """

        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        min = self.get_argument('min', type=int)
        max = self.get_argument('max', type=int)

        logging.info("Autoscaling '%s' worker by '%s'",
                     workername, (min, max))
        response = celery.control.broadcast('autoscale',
                                            arguments={'min': min, 'max': max},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(message="Autoscaling '%s' worker "
                                    "(min=%s, max=%s)" % (
                                        workername, min, max)))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to autoscale '%s' worker: %s" % (
                workername, self.error_reason(workername, response)
            ))


class WorkerQueueAddConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Start consuming from a queue

**Example request**:

.. sourcecode:: http

  POST /api/worker/queue/add-consumer/celery@worker2?queue=sample-queue
  Content-Length: 0
  Content-Type: application/x-www-form-urlencoded; charset=utf-8
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 40
  Content-Type: application/json; charset=UTF-8

  {
      "message": "add consumer sample-queue"
  }

:query queue: the name of a new queue
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: failed to add consumer
:statuscode 404: unknown worker
        """
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        queue = self.get_argument('queue')

        logging.info("Adding consumer '%s' to worker '%s'",
                     queue, workername)
        response = celery.control.broadcast('add_consumer',
                                            arguments={'queue': queue},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to add '%s' consumer to '%s' worker: %s" % (
                workername, self.error_reason(workername, response)
            ))


class WorkerQueueCancelConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
        """
Stop consuming from a queue

**Example request**:

.. sourcecode:: http

  POST /api/worker/queue/cancel-consumer/celery@worker2?queue=sample-queue
  Content-Length: 0
  Content-Type: application/x-www-form-urlencoded; charset=utf-8
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 52
  Content-Type: application/json; charset=UTF-8

  {
      "message": "no longer consuming from sample-queue"
  }

:query queue: the name of queue
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 403: failed to cancel consumer
:statuscode 404: unknown worker
        """
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        queue = self.get_argument('queue')

        logging.info("Canceling consumer '%s' from worker '%s'",
                     queue, workername)
        response = celery.control.broadcast('cancel_consumer',
                                            arguments={'queue': queue},
                                            destination=[workername],
                                            reply=True)
        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write(
                "Failed to cancel '%s' consumer from '%s' worker: %s" % (
                    workername, self.error_reason(workername, response)
                ))


class TaskRevoke(BaseHandler):
    @web.authenticated
    def post(self, taskid):
        """
Revoke a task

**Example request**:

.. sourcecode:: http

  POST /api/task/revoke/1480b55c-b8b2-462c-985e-24af3e9158f9?terminate=true
  Content-Length: 0
  Content-Type: application/x-www-form-urlencoded; charset=utf-8
  Host: localhost:5555

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 61
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Revoked '1480b55c-b8b2-462c-985e-24af3e9158f9'"
  }

:query terminate: terminate the task if it is running
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
        """
        logging.info("Revoking task '%s'", taskid)
        celery = self.application.celery_app
        terminate = self.get_argument('terminate', default=False, type=bool)
        celery.control.revoke(taskid, terminate=terminate)
        self.write(dict(message="Revoked '%s'" % taskid))


class TaskTimout(ControlHandler):
    @web.authenticated
    def post(self, taskname):
        """
Change soft and hard time limits for a task

**Example request**:

.. sourcecode:: http

    POST /api/task/timeout/tasks.sleep HTTP/1.1
    Content-Length: 44
    Content-Type: application/x-www-form-urlencoded; charset=utf-8
    Host: localhost:5555

    soft=30&hard=100&workername=celery%40worker1

**Example response**:

.. sourcecode:: http

    HTTP/1.1 200 OK
    Content-Length: 46
    Content-Type: application/json; charset=UTF-8

    {
        "message": "new rate limit set successfully"
    }

:query workername: worker name
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task/worker
        """
        celery = self.application.celery_app

        workername = self.get_argument('workername')
        hard = self.get_argument('hard', default=None, type=float)
        soft = self.get_argument('soft', default=None, type=float)

        if taskname not in celery.tasks:
            raise web.HTTPError(404, "Unknown task '%s'" % taskname)
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)

        logging.info("Setting timeouts for '%s' task (%s, %s)",
                     taskname, soft, hard)
        destination = [workername] if workername is not None else None
        response = celery.control.time_limit(taskname, reply=True,
                                             hard=hard, soft=soft,
                                             destination=destination)

        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set timeouts: '%s'" %
                       self.error_reason(taskname, response))


class TaskRateLimit(ControlHandler):
    @web.authenticated
    def post(self, taskname):
        """
Change rate limit for a task

**Example request**:

.. sourcecode:: http

    POST /api/task/rate-limit/tasks.sleep HTTP/1.1
    Content-Length: 41
    Content-Type: application/x-www-form-urlencoded; charset=utf-8
    Host: localhost:5555

    ratelimit=200&workername=celery%40worker1

**Example response**:

.. sourcecode:: http

  HTTP/1.1 200 OK
  Content-Length: 61
  Content-Type: application/json; charset=UTF-8

  {
      "message": "Revoked '1480b55c-b8b2-462c-985e-24af3e9158f9'"
  }

:query terminate: terminate the task if it is running
:reqheader Authorization: optional OAuth token to authenticate
:statuscode 200: no error
:statuscode 401: unauthorized request
:statuscode 404: unknown task/worker
        """
        celery = self.application.celery_app

        workername = self.get_argument('workername')
        ratelimit = self.get_argument('ratelimit')

        if taskname not in celery.tasks:
            raise web.HTTPError(404, "Unknown task '%s'" % taskname)
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)

        logging.info("Setting '%s' rate limit for '%s' task",
                     ratelimit, taskname)
        destination = [workername] if workername is not None else None
        response = celery.control.rate_limit(taskname,
                                             ratelimit,
                                             reply=True,
                                             destination=destination)
        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set rate limit: '%s'" %
                       self.error_reason(taskname, response))
