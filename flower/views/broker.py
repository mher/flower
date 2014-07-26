from __future__ import absolute_import

from tornado import web
from tornado import gen

from ..views import BaseHandler
from ..utils.broker import Broker
from ..api.control import ControlHandler


class BrokerView(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        app = self.application.celery_app
        if app.transport == 'amqp' and app.broker_api:
            mgmnt_api = self.broker_api
        else:
            mgmnt_api = None
        broker = Broker(app.connection().as_uri(include_password=True),
                        mgmnt_api=mgmnt_api)
        queue_names = ControlHandler.get_active_queue_names()
        queues = yield broker.queues(queue_names)
        self.render("broker.html", broker_url=app.connection().as_uri(),
                                   queues=queues)
