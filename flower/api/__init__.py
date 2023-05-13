import tornado.web
from ..views import BaseHandler

class BaseApiHandler(BaseHandler):
    def prepare(self):
        if self.application.options.auth:
            raise tornado.web.HTTPError(405, "api is not available when auth is enabled")

    def write_error(self, status_code, **kwargs):
        exc_info = kwargs.get('exc_info')
        log_message = exc_info[1].log_message
        if log_message:
            self.write(log_message)
        self.set_status(status_code)
        self.finish()
