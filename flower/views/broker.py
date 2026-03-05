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

        queue_names = self.get_active_queue_names()
        names_key = frozenset(queue_names)

        # Get broker URI once — reuse for both Broker creation and display
        with app.capp.connection(connect_timeout=1.0) as conn:
            broker_uri = conn.as_uri(include_password=True)
            broker_url = conn.as_uri()

        # Check cache first
        queues = app.get_cached_queue_stats(names_key)
        if queues is None:
            try:
                broker = Broker(broker_uri,
                                http_api=http_api, broker_options=self.capp.conf.broker_transport_options,
                                broker_use_ssl=self.capp.conf.broker_use_ssl)
            except NotImplementedError as exc:
                raise web.HTTPError(
                    404, f"'{app.transport}' broker is not supported") from exc

            queues = []
            try:
                queues = await broker.queues(queue_names)
                app.set_queue_cache(names_key, queues)
            except Exception as e:
                logger.error("Unable to get queues: '%s'", e)
            finally:
                if hasattr(broker, 'close'):
                    broker.close()

        self.render("broker.html",
                    broker_url=broker_url,
                    queues=queues)
