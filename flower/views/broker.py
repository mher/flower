import logging

from tornado import web
from tornado import gen

from ..views import BaseHandler
from ..utils.broker import Broker
from ..api.control import ControlHandler


logger = logging.getLogger(__name__)


class BrokerView(BaseHandler):
    @web.authenticated
    async def get(self):
        app = self.application
        broker_options = self.capp.conf.broker_transport_options

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        broker_use_ssl = None
        if self.capp.conf.broker_use_ssl:
            broker_use_ssl = self.capp.conf.broker_use_ssl

        try:
            broker = Broker(app.capp.connection(connect_timeout=1.0).as_uri(include_password=True),
                            http_api=http_api, broker_options=broker_options, broker_use_ssl=broker_use_ssl)
        except NotImplementedError:
            raise web.HTTPError(
                404, "'%s' broker is not supported" % app.transport)

        queues = {}
        try:
            queue_names = self.get_active_queue_names()
            if not queue_names:
                queue_names = set([self.capp.conf.task_default_queue]) |\
                        set([q.name for q in self.capp.conf.task_queues or [] if q.name])

            queues = await broker.queues(sorted(queue_names))
        except Exception as e:
            logger.error("Unable to get queues: '%s'", e)

        self.render("broker.html",
                    broker_url=app.capp.connection().as_uri(),
                    queues=queues)
