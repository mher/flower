from __future__ import absolute_import

import json
import re

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import tornado.gen
import tornado.web
import tornado.auth

from tornado.options import options
from celery.utils.imports import instantiate

from ..views import BaseHandler


class GoogleAuth2LoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    _OAUTH_SETTINGS_KEY = 'oauth'

    @tornado.gen.coroutine
    def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            yield self._on_auth(user)
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'}
            )

    @tornado.gen.coroutine
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(403, 'Google auth failed')
        access_token = user['access_token']

        try:
            response = yield self.get_auth_http_client().fetch(
                'https://www.googleapis.com/userinfo/v2/me',
                headers={'Authorization': 'Bearer %s' % access_token})
        except Exception as e:
            raise tornado.web.HTTPError(403, 'Google auth failed: %s' % e)

        email = json.loads(response.body.decode('utf-8'))['email']
        if not re.match(self.application.options.auth, email):
            message = (
                "Access denied to '{email}'. Please use another account or "
                "ask your admin to add your email to flower --auth."
            ).format(email=email)
            raise tornado.web.HTTPError(403, message)

        self.set_secure_cookie("user", str(email))

        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next[0] != '/':
            next_ = '/' + next_

        self.redirect(next_)


class LoginHandler(BaseHandler):
    def __new__(cls, *args, **kwargs):
        return instantiate(options.auth_provider, *args, **kwargs)


class GithubLoginHandler(BaseHandler, tornado.auth.OAuth2Mixin):

    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'oauth'

    @tornado.gen.coroutine
    def get_authenticated_user(self, redirect_uri, code):
        body = urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]['secret'],
            "grant_type": "authorization_code",
        })

        response = yield self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'}, body=body)

        if response.error:
            raise tornado.auth.AuthError(
                'OAuth authenticator error: %s' % str(response))

        raise tornado.gen.Return(json.loads(response.body.decode('utf-8')))

    @tornado.gen.coroutine
    def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            yield self._on_auth(user)
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['user:email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto'}
            )

    @tornado.gen.coroutine
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = user['access_token']

        response = yield self.get_auth_http_client().fetch(
            'https://api.github.com/user/emails',
            headers={'Authorization': 'token ' + access_token,
                     'User-agent': 'Tornado auth'})


        emails = [email['email'].lower() for email in json.loads(response.body.decode('utf-8'))
                  if email['verified'] and re.match(self.application.options.auth, email['email'])]

        if not emails:
            message = (
                "Access denied. Please use another account or "
                "ask your admin to add your email to flower --auth."
            )
            raise tornado.web.HTTPError(403, message)

        self.set_secure_cookie("user", str(emails.pop()))

        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_
        self.redirect(next_)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.render('404.html', message='Successfully logged out!')
