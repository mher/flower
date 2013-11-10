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
        if not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        logging.info("Shutting down '%s' worker", workername)
        celery.control.broadcast('shutdown', destination=[workername])
        self.write(dict(message="Shutting down!"))


class WorkerPoolRestart(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write("Failed to restart the '%s' pool: %s" %
                    (workername, self.error_reason(workername, response)))


class WorkerPoolGrow(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write(dict(message="Growing '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to grow '%s' worker's pool" %
                    (workername, self.error_reason(workername, response)))


class WorkerPoolShrink(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write(dict(
                message="Shrinking '%s' worker's pool" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to shrink '%s' worker's pool: %s" %
                    (workername, self.error_reason(workername, response)))


class WorkerPoolAutoscale(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write(dict(message="Autoscaling '%s' worker" % workername))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to autoscale '%s' worker: %s" %
                    (workername, self.error_reason(workername, response)))


class WorkerQueueAddConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write("Failed to add '%s' consumer to '%s' worker: %s" %
                    (workername, self.error_reason(workername, response)))


class WorkerQueueCancelConsumer(ControlHandler):
    @web.authenticated
    def post(self, workername):
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
            self.write("Failed to cancel '%s' consumer from '%s' worker: %s" %
                    (workername, self.error_reason(workername, response)))


class TaskRevoke(BaseHandler):
    @web.authenticated
    def post(self, taskid):
        logging.info("Revoking task '%s'", taskid)
        celery = self.application.celery_app
        terminate = self.get_argument('terminate', default=False, type=bool)
        celery.control.revoke(taskid, terminate=terminate)
        self.write(dict(message="Revoked '%s'" % taskid))


class TaskTimout(ControlHandler):
    @web.authenticated
    def post(self, workername=None):
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        taskname = self.get_argument('taskname', default=None)
        hard = self.get_argument('hard', default=None, type=float)
        soft = self.get_argument('soft', default=None, type=float)

        logging.info("Setting timeouts for '%s' task (%s, %s)",
                     taskname, soft, hard)
        response = celery.control.time_limit(taskname, reply=True,
                                             hard=hard, soft=soft,
                                             destination=[workername])
        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set timeouts: '%s'" %
                    self.error_reason(workername, response))


class TaskRateLimit(ControlHandler):
    @web.authenticated
    def post(self, workername=None):
        if workername is not None and not self.is_worker(workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        celery = self.application.celery_app

        taskname = self.get_argument('taskname', None)
        ratelimit = self.get_argument('ratelimit', type=int)

        logging.info("Setting '%s' rate limit for '%s' task",
                     ratelimit, taskname)
        response = celery.control.rate_limit(taskname,
                                             ratelimit,
                                             reply=True,
                                             destination=[workername])
        if response and 'ok' in response[0][workername]:
            self.write(dict(message=response[0][workername]['ok']))
        else:
            logging.error(response)
            self.set_status(403)
            self.write("Failed to set rate limit: '%s'" %
                    self.error_reason(workername, response))
