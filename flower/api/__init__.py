import tornado.websocket
from ..views import BaseHandler

class BaseWebSocketHandler(tornado.websocket.WebSocketHandler):
    # listeners = [], should be created in derived class

    def open(self):
        listeners = self.listeners
        listeners.append(self)

    def on_message(self, message):
        pass

    def on_close(self):
        listeners = self.listeners
        if self in listeners:
            listeners.remove(self)

    @classmethod
    def send_message(cls, message):
        for l in cls.listeners:
            l.write_message(message)

    def check_origin(self, origin):
        return True

class BaseApiHandler(BaseHandler):
    def prepare(self):
        if self.application.options.basic_auth or self.application.options.auth:
            raise tornado.web.HTTPError(405, "api is not available when auth is enabled")
