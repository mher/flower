import logging

from tornado import web

from ..views import BaseHandler

logger = logging.getLogger(__name__)


class BrokerView(BaseHandler):
    @web.authenticated
    async def get(self):
        broker = self.get_broker()
        try:
            queues = await broker.queues(self.get_active_queue_names())
        except Exception as e:
            queues = []
            logger.error("Unable to get queues: '%s'", e)

        self.render("broker.html",
                    broker_url=self.application.broker_uri,
                    queues=queues)
