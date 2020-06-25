from __future__ import absolute_import

from collections import defaultdict

from tornado import web
from tornado import gen
from celery import states
import prometheus_client

from ..views import BaseHandler
from ..utils.broker import Broker
from ..api.control import ControlHandler


class Monitor(BaseHandler):
    @web.authenticated
    def get(self):
        self.render("monitor.html")


class SucceededTaskMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = self.get_argument('lastquery', type=float)
        state = self.application.events.state

        data = defaultdict(int)
        for _, task in state.itertasks():
            if (timestamp < task.timestamp and task.state == states.SUCCESS):
                data[task.worker.hostname] += 1
        for worker in state.workers:
            if worker not in data:
                data[worker] = 0

        self.write(data)


class TimeToCompletionMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = self.get_argument('lastquery', type=float)
        state = self.application.events.state

        execute_time = 0
        queue_time = 0
        num_tasks = 0
        for _, task in state.itertasks():
            if (timestamp < task.timestamp and task.state == states.SUCCESS):
                # eta can make "time in queue" look really scary.
                if task.eta is not None:
                    continue

                if task.started is None or task.received is None or\
                        task.succeeded is None:
                    continue

                queue_time += task.started - task.received
                execute_time += task.succeeded - task.started
                num_tasks += 1

        avg_queue_time = (queue_time / num_tasks) if num_tasks > 0 else 0
        avg_execution_time = (execute_time / num_tasks) if num_tasks > 0 else 0

        result = {
            "Time in a queue": avg_queue_time,
            "Execution time": avg_execution_time,
        }
        self.write(result)


class FailedTaskMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = self.get_argument('lastquery', type=float)
        state = self.application.events.state

        data = defaultdict(int)
        for _, task in state.itertasks():
            if (timestamp < task.timestamp and task.state == states.FAILURE):
                data[task.worker.hostname] += 1
        for worker in state.workers:
            if worker not in data:
                data[worker] = 0

        self.write(data)


class BrokerMonitor(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        app = self.application
        broker_options = self.capp.conf.BROKER_TRANSPORT_OPTIONS

        capp = app.capp

        try:
            broker_use_ssl = None
            if self.capp.conf.BROKER_USE_SSL:
                broker_use_ssl = self.capp.conf.BROKER_USE_SSL
            broker = Broker(capp.connection().as_uri(include_password=True),
                            http_api=app.options.broker_api, broker_use_ssl=broker_use_ssl,
                            broker_options=broker_options)
        except NotImplementedError:
            self.write({})
            return

        queue_names = ControlHandler.get_active_queue_names()
        if not queue_names:
            queue_names = set([self.capp.conf.CELERY_DEFAULT_QUEUE]) | \
                          set([q.name for q in self.capp.conf.CELERY_QUEUES or [] if q.name])
        queues = yield broker.queues(queue_names)

        data = defaultdict(int)
        for queue in queues:
            data[queue['name']] = queue.get('messages', 0)

        self.write(data)

class Metrics(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        self.write(prometheus_client.generate_latest())
