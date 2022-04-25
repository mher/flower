from tornado import web
import tornado.websocket

from ..views import BaseHandler, RequireAuthMixin

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

    # This method override is required because Tornado by default does not
    # require authentication to open websocket connections.
    # The @web.authenticated decorator doesn't seem to work for WebSocketHandler
    async def get(self, *args, **kwargs):
        if not self.get_current_user():
            raise tornado.web.HTTPError(401)

        return await super(BaseWebSocketHandler, self).get(*args, **kwargs)

class BaseApiHandler(BaseHandler):
    def get_current_user(self):
        if self.application.options.dangerous_allow_unauth_api:
            return True

        # API is fully disabled if no authentication is configured
        if not (self.application.options.basic_auth or self.application.options.auth):
            raise tornado.web.HTTPError(401)

        return super(RequireAuthMixin, self).get_current_user()
