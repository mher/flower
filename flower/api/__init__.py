import tornado.web
from ..views import BaseHandler

class BaseApiHandler(BaseHandler):
    def prepare(self):
        if self.application.options.basic_auth or self.application.options.auth:
            raise tornado.web.HTTPError(405, "api is not available when auth is enabled")
