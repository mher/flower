import prometheus_client

from tornado import gen

from ..events import EventsState
from ..views import BaseHandler


class Metrics(BaseHandler):
    @gen.coroutine
    def get(self):
        events_state: EventsState = self.application.events.state
        events_state.remove_metrics_for_offline_workers()

        self.write(prometheus_client.generate_latest())
        self.set_header("Content-Type", "text/plain")


class Healthcheck(BaseHandler):
    @gen.coroutine
    def get(self):
        self.write("OK")
