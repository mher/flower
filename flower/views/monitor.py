from __future__ import absolute_import

from collections import defaultdict

from ..views import BaseHandler
from ..events import Events


class Monitor(BaseHandler):
    def get(self):
        self.render("monitor.html")


class TaskNumberMonitor(BaseHandler):
    def get(self):
        timestamp = float(self.get_argument('lastquery'))
        state = Events().state

        data = defaultdict(int)
        for _, task in state.itertasks():
            if timestamp < task.timestamp:
                data[task.worker.hostname] += 1
        for worker in state.workers:
            if worker not in data:
                data[worker] = 0

        self.write(data)
