from __future__ import absolute_import

try:
    from urllib.parse import urlparse, parse_qsl, urlencode
except ImportError:
    from urlparse import urlparse, parse_qsl
    from urllib import urlencode

import re
import tornado.web
import tornado.auth

from .. import settings
from ..views import BaseHandler


class LoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        callback_uri = None
        if settings.URL_PREFIX:
            qs = dict(parse_qsl(urlparse(self.request.uri).query))
            next = qs.get('next', '/')
            callback_uri = self.absolute_url('/login')
            callback_uri += '?' + urlencode(dict(next=next))

        self.authenticate_redirect(callback_uri=callback_uri)

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'Google auth failed')
        if not re.match(self.application.auth, user['email']):
            raise tornado.web.HTTPError(
                404,
                "Access denied to '{email}'. "
                "Please use another account or ask your admin to "
                "add your email to flower --auth".format(**user))

        self.set_secure_cookie("user", str(user['email']))

        next = self.get_argument('next', '/')
        if settings.URL_PREFIX:
            next = self.absolute_url(next)

        self.redirect(next)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.render('404.html', message='Successfully logged out!')
