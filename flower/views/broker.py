from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import BrokerModel


class BrokerView(BaseHandler):
    @web.authenticated
    def get(self):
        broker = BrokerModel(self.application)
        self.render("broker.html", broker=broker)
