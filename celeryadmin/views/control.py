from __future__ import absolute_import

import logging

import celery

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel

is_worker = WorkersModel.is_worker
celery = celery.current_app


class ShutdownWorker(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        logging.info("Shutting down '%s' worker" % workername)
        celery.control.broadcast('shutdown', destination=[workername])
        self.write(dict(message="Shutting down!"))


class RestartWorkerPool(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        logging.info("Restarting '%s' worker's pool" % workername)
        response = celery.control.broadcast('pool_restart',
                                             arguments={'reload': False},
                                             destination=[workername],
                                             reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(
                message="Restarting '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to restart the '%s' pool" % workername)


class TaskRateLimit(BaseHandler):
    def post(self, workername=None):
        if workername is not None and not is_worker(workername):
            raise web.HTTPError(404)

        taskname = self.get_argument('taskname', None)
        ratelimit = int(self.get_argument('ratelimit'))

        logging.info("Setting '%s' rate limit for '%s' task" %
                     (ratelimit, taskname))
        response = celery.control.rate_limit(taskname,
                                              ratelimit,
                                              reply=True,
                                              destination=[workername])
        if 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set rate limit: '%s'" %
                       response[0][workername]['error'])


class TaskTimout(BaseHandler):
    def post(self, workername=None):
        if workername is not None and not is_worker(workername):
            raise web.HTTPError(404)

        taskname = self.get_argument('taskname', None)
        hard = self.get_argument('hard-timeout', None)
        soft = self.get_argument('soft-timeout', None)
        hard = hard and float(hard)
        soft = soft and float(soft)

        logging.info("Setting timeouts for '%s' task" % taskname)
        response = celery.control.time_limit(taskname, hard, soft,
                                             reply=True,
                                             destination=[workername])
        if 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set timeouts: '%s'" %
                       response[0][workername]['error'])


class WorkerPoolGrow(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        n = int(self.get_argument('n', 1))

        logging.info("Growing '%s' worker's pool by '%s'" % (workername, n))
        response = celery.control.broadcast('pool_grow',
                                             arguments={'n': n},
                                             destination=[workername],
                                             reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(message="Growing '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to grow '%s' worker's pool" % workername)


class WorkerPoolShrink(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        n = int(self.get_argument('n', 1))

        logging.info("Shrinking '%s' worker's pool by '%s'" % (workername, n))
        response = celery.control.broadcast('pool_shrink',
                                             arguments={'n': n},
                                             destination=[workername],
                                             reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(
                message="Shrinking '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to restart '%s' worker's pool" % workername)


class WorkerPoolAutoscale(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        min = int(self.get_argument('min'))
        max = int(self.get_argument('max'))

        logging.info("Autoscaling '%s' worker by '%s'" %
                     (workername, (min, max)))
        response = celery.control.broadcast('autoscale',
                        arguments={'min': min, 'max': max},
                        destination=[workername],
                        reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(message="Autoscaling '%s' worker" % workername))
        else:
            logging.error(response)
            error = response[0][workername]['error']
            self.set_status(403)
            self.write("Failed to autoscale '%s' worker: %s" %
                       (workername, error))


class WorkerQueueAddConsumer(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        queue = self.get_argument('queue')

        logging.info("Adding consumer '%s' to worker '%s'" %
                     (queue, workername))
        response = celery.control.broadcast('add_consumer',
                        arguments={'queue': queue},
                        destination=[workername],
                        reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            error = response[0][workername]['error']
            self.set_status(403)
            self.write("Failed to add '%s' consumer to '%s' worker: %s" %
                       (queue, workername, error))


class WorkerQueueCancelConsumer(BaseHandler):
    def post(self, workername):
        if not is_worker(workername):
            raise web.HTTPError(404)

        queue = self.get_argument('queue')

        logging.info("Canceling consumer '%s' from worker '%s'" %
                     (queue, workername))
        response = celery.control.broadcast('cancel_consumer',
                        arguments={'queue': queue},
                        destination=[workername],
                        reply=True)
        if 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            error = response[0][workername]['error']
            self.set_status(403)
            self.write("Failed to cancel '%s' consumer from '%s' worker: %s" %
                       (queue, workername, error))
