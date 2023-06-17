import os

import tornado.web

from ..utils import strtobool
from ..views import BaseHandler


class BaseApiHandler(BaseHandler):
    def prepare(self):
        enable_api = strtobool(os.environ.get(
            'FLOWER_UNAUTHENTICATED_API') or "false")
        if not (self.application.options.basic_auth or self.application.options.auth) and not enable_api:
            raise tornado.web.HTTPError(
                401, "FLOWER_UNAUTHENTICATED_API environment variable is required to enable API without authentication")

    def write_error(self, status_code, **kwargs):
        exc_info = kwargs.get('exc_info')
        log_message = exc_info[1].log_message
        if log_message:
            self.write(log_message)
        self.set_status(status_code)
        self.finish()
