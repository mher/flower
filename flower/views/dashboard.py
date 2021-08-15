import logging

from tornado import web
from tornado import gen

from ..events import EventsState
from ..views import BaseHandler


logger = logging.getLogger(__name__)


class DashboardView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        refresh = self.get_argument('refresh', default=False, type=bool)
        json = self.get_argument('json', default=False, type=bool)

        events_state: EventsState = self.application.events.state

        if refresh:
            try:
                self.application.update_workers()
            except Exception as e:
                logger.exception('Failed to update workers: %s', e)

        workers = events_state.get_online_workers()
        if json:
            self.write(dict(data=list(workers.values())))
        else:
            self.render("dashboard.html",
                        workers=workers,
                        broker=self.application.capp.connection().as_uri(),
                        autorefresh=1 if self.application.options.auto_refresh else 0)
