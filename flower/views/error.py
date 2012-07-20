from __future__ import absolute_import

import tornado.web

from ..views import BaseHandler


class NotFoundErrorHandler(BaseHandler):
    def get(self):
        raise tornado.web.HTTPError(404)
