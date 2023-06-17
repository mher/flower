import logging

from tornado import web

from ..utils.broker import Broker
from ..views import BaseHandler

logger = logging.getLogger(__name__)


class BrokerView(BaseHandler):
    @web.authenticated
    async def get(self):
        app = self.application

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        try:
            broker = Broker(app.capp.connection(connect_timeout=1.0).as_uri(include_password=True),
                            http_api=http_api, broker_options=self.capp.conf.broker_transport_options,
                            broker_use_ssl=self.capp.conf.broker_use_ssl)
        except NotImplementedError as exc:
            raise web.HTTPError(
                404, f"'{app.transport}' broker is not supported") from exc

        try:
            queues = await broker.queues(self.get_active_queue_names())
        except Exception as e:
            logger.error("Unable to get queues: '%s'", e)

        self.render("broker.html",
                    broker_url=app.capp.connection().as_uri(),
                    queues=queues)
