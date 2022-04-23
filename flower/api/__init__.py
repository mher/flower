from tornado import web
import tornado.websocket

from ..views import BaseHandler

class RequireAuthMixin():
    def get_current_user(self):
        # API is fully disabled if no authentication is configured
        if not (self.application.options.basic_auth or self.application.options.auth):
            raise tornado.web.HTTPError(401)

        return super(BaseApiHandler, self).get_current_user(self)

class BaseWebSocketHandler(RequireAuthMixin, tornado.websocket.WebSocketHandler):
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

    # This decorator and method are required because Tornado by default does not
    # require authentication to open websocket connections
    @web.authenticated
    def get(self, *args, **kwargs):
        super()


class BaseApiHandler(RequireAuthMixin, BaseHandler):
    pass
