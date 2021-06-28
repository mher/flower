import logging

from tornado import web
from tornado import gen

from ..views import BaseHandler
from ..utils.broker import Broker
from ..api.control import ControlHandler


logger = logging.getLogger(__name__)


class BrokerView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        app = self.application
        broker_options = self.capp.conf.BROKER_TRANSPORT_OPTIONS

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        broker_use_ssl = None
        if self.capp.conf.BROKER_USE_SSL:
            broker_use_ssl = self.capp.conf.BROKER_USE_SSL

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
                queue_names = set([self.capp.conf.CELERY_DEFAULT_QUEUE]) |\
                        set([q.name for q in self.capp.conf.CELERY_QUEUES or [] if q.name])

            queues = yield broker.queues(sorted(queue_names))
        except Exception as e:
            logger.error("Unable to get queues: '%s'", e)

        self.render("broker.html",
                    broker_url=app.capp.connection().as_uri(),
                    queues=queues)
