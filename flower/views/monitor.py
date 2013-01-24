from __future__ import absolute_import

from collections import defaultdict

from tornado import web
from celery import states

from ..views import BaseHandler


class Monitor(BaseHandler):
    @web.authenticated
    def get(self):
        self.render("monitor.html")


class SucceededTaskMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = float(self.get_argument('lastquery'))
        state = self.application.events.state

        data = defaultdict(int)
        for _, task in state.itertasks():
            if timestamp < task.timestamp and task.state == states.SUCCESS:
                data[task.worker.hostname] += 1
        for worker in state.workers:
            if worker not in data:
                data[worker] = 0

        self.write(data)


class TimeToCompletionMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = float(self.get_argument('lastquery'))
        state = self.application.events.state

        total_time = 0
        num_tasks = 0
        for _, task in state.itertasks():
            if timestamp < task.timestamp and task.state == states.SUCCESS:
                if task.eta is None:
                    diff = task.succeeded - task.received
                    total_time += diff
                    num_tasks += 1

        result = {
            "average_time": (total_time / num_tasks) if num_tasks > 0 else 0
        }
        self.write(result)


class FailedTaskMonitor(BaseHandler):
    @web.authenticated
    def get(self):
        timestamp = float(self.get_argument('lastquery'))
        state = self.application.events.state

        data = defaultdict(int)
        for _, task in state.itertasks():
            if timestamp < task.timestamp and task.state == states.FAILURE:
                data[task.worker.hostname] += 1
        for worker in state.workers:
            if worker not in data:
                data[worker] = 0

        self.write(data)
