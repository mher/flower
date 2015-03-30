from __future__ import absolute_import

import re
import json

import tornado.web
import tornado.auth

from tornado import httpclient

from ..views import BaseHandler


class LoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    @tornado.web.asynchronous
    def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
                callback=self._on_auth,
            )
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'}
            )

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'Google auth failed')
        access_token = user['access_token']
        response = httpclient.HTTPClient().fetch(
            'https://www.googleapis.com/plus/v1/people/me',
            headers={'Authorization': 'Bearer %s' % access_token})
        email = json.loads(response.body.decode('utf-8'))['emails'][0]['value']
        if not re.match(self.application.options.auth, email):
            message = (
                "Access denied to '{email}'. Please use another account or "
                "ask your admin to add your email to flower --auth."
            ).format(email=email)
            raise tornado.web.HTTPError(404, message)

        self.set_secure_cookie("user", str(email))

        next = self.get_argument('next', '/')
        self.redirect(next)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.render('404.html', message='Successfully logged out!')
