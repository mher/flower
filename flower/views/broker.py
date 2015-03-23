from __future__ import absolute_import

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

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        broker = Broker(app.capp.connection().as_uri(include_password=True),
                        http_api=http_api)
        queue_names = ControlHandler.get_active_queue_names()
        queues = yield broker.queues(sorted(queue_names))

        self.render("broker.html",
                    broker_url=app.capp.connection().as_uri(),
                    queues=queues)
