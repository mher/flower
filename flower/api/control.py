from __future__ import absolute_import

import logging

from tornado import web

from ..views import BaseHandler
from ..models import WorkersModel


class ControlHandler(BaseHandler):
    def is_worker(self, name):
        return WorkersModel.is_worker(self.application, name)


class WorkerShutDown(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        logging.info("Shutting down '%s' worker" % workername)
        celery.control.broadcast('shutdown', destination=[workername])
        self.write(dict(message="Shutting down!"))


class WorkerPoolRestart(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class WorkerPoolGrow(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class WorkerPoolShrink(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class WorkerPoolAutoscale(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class WorkerQueueAddConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class WorkerQueueCancelConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class TaskRevoke(BaseHandler):
    @web.authenticated
    def post(self, taskid):
        logging.info("Revoking task '%s'" % taskid)
        celery = self.application.celery_app
        terminate = bool(self.get_argument('terminate', False))
        celery.control.revoke(taskid, terminate=terminate)
        self.write(dict(message="Revoked '%s'" % taskid))


class TaskTimout(ControlHandler):
    @web.authenticated
    def post(self, workername=None):
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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


class TaskRateLimit(ControlHandler):
    @web.authenticated
    def post(self, workername=None):
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

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
