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
        capp = app.celery_app

        mgmnt_api = None

        if app.transport == 'amqp' and app.broker_api:
            mgmnt_api = app.broker_api

        broker = Broker(capp.connection().as_uri(include_password=True),
                        mgmnt_api=mgmnt_api)
        queue_names = ControlHandler.get_active_queue_names()
        queues = yield broker.queues(queue_names)

        self.render("broker.html",
                    broker_url=capp.connection().as_uri(),
                    queues=queues)
