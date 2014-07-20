from __future__ import absolute_import

try:
    from urllib.parse import urlparse, parse_qsl, urlencode
except ImportError:
    from urlparse import urlparse, parse_qsl
    from urllib import urlencode

import re
import functools
import tornado.web
import tornado.auth
from tornado import httpclient
import json

from .. import settings
from ..views import BaseHandler


class LoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    @tornado.web.asynchronous
    def get(self):
        callback_uri = None
        if settings.URL_PREFIX:
            qs = dict(parse_qsl(urlparse(self.request.uri).query))
            next = qs.get('next', '/')
            callback_uri = self.absolute_url('/login')
            callback_uri += '?' + urlencode(dict(next=next))

        if self.get_argument('code', False):
            self.get_authenticated_user(
                redirect_uri=self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri'],
                code=self.get_argument('code'),
                callback=functools.partial(self._on_auth),
            )
        else:
            self.authorize_redirect(
                redirect_uri=self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri'],
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'}
            )


    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'Google auth failed')
        access_token = user['access_token']
        response = httpclient.HTTPClient().fetch('https://www.googleapis.com/plus/v1/people/me', headers={'Authorization': 'Bearer %s' % access_token})
        email = json.loads(response.body.decode('utf-8'))['emails'][0]['value']
        if not re.match(self.application.auth, email):
            raise tornado.web.HTTPError(
                404,
                "Access denied to '{email}'. "
                "Please use another account or ask your admin to "
                "add your email to flower --auth".format(**user))

        self.set_secure_cookie("user", str(email))

        next = self.get_argument('next', '/')
        if settings.URL_PREFIX:
            next = self.absolute_url(next)

        self.redirect(next)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.render('404.html', message='Successfully logged out!')
