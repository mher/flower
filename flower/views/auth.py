import json
import re
import os
import uuid

from urllib.parse import urlencode
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
                extra_params={'approval_prompt': ''}
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
        if self.application.options.url_prefix and next_[0] != '/':
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
                extra_params={'approval_prompt': ''}
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


class GitLabLoginHandler(BaseHandler, tornado.auth.OAuth2Mixin):

    _OAUTH_AUTHORIZE_URL = 'https://gitlab.com/oauth/authorize'
    _OAUTH_ACCESS_TOKEN_URL = 'https://gitlab.com/oauth/token'
    _OAUTH_NO_CALLBACKS = False

    @tornado.gen.coroutine
    def get_authenticated_user(self, redirect_uri, code):
        body = urlencode({
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': self.settings['oauth']['key'],
            'client_secret': self.settings['oauth']['secret'],
            'grant_type': 'authorization_code',
        })
        response = yield self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'},
            body=body
        )
        if response.error:
            raise tornado.auth.AuthError('OAuth authenticator error: %s' % str(response))
        raise tornado.gen.Return(json.loads(response.body.decode('utf-8')))

    @tornado.gen.coroutine
    def get(self):
        redirect_uri = self.settings['oauth']['redirect_uri']
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            yield self._on_auth(user)
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings['oauth']['key'],
                scope=['read_api'],
                response_type='code',
                extra_params={'approval_prompt': ''},
            )

    @tornado.gen.coroutine
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = user['access_token']
        allowed_groups = os.environ.get('FLOWER_GITLAB_AUTH_ALLOWED_GROUPS', '')
        allowed_groups = [group.strip() for group in allowed_groups.split(',') if group]

        # Check user email address against regexp
        try:
            response = yield self.get_auth_http_client().fetch(
                'https://gitlab.com/api/v4/user',
                headers={'Authorization': 'Bearer ' + access_token,
                         'User-agent': 'Tornado auth'}
            )
        except Exception as e:
            raise tornado.web.HTTPError(403, 'GitLab auth failed: %s' % e)

        user_email = json.loads(response.body.decode('utf-8'))['email']
        email_allowed = re.match(self.application.options.auth, user_email)

        # Check user's groups against list of allowed groups
        matching_groups = []
        if allowed_groups:
            min_access_level = os.environ.get('FLOWER_GITLAB_MIN_ACCESS_LEVEL', '20')
            response = yield self.get_auth_http_client().fetch(
                'https://gitlab.com/api/v4/groups?min_access_level=%s' % (min_access_level,),
                headers={
                    'Authorization': 'Bearer ' + access_token,
                    'User-agent': 'Tornado auth'
                }
            )
            matching_groups = [
                group['id']
                for group in json.loads(response.body.decode('utf-8'))
                if group['full_path'] in allowed_groups
            ]

        if not email_allowed or (allowed_groups and len(matching_groups) == 0):
            message = 'Access denied. Please use another account or contact your admin.'
            raise tornado.web.HTTPError(403, message)

        self.set_secure_cookie('user', str(user_email))
        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_
        self.redirect(next_)


class OktaLoginHandler(BaseHandler, tornado.auth.OAuth2Mixin):
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'oauth'

    @property
    def base_url(self):
        return os.environ.get('FLOWER_OAUTH2_OKTA_BASE_URL')

    @property
    def _OAUTH_AUTHORIZE_URL(self):
        return "{}/v1/authorize".format(self.base_url)

    @property
    def _OAUTH_ACCESS_TOKEN_URL(self):
        return "{}/v1/token".format(self.base_url)

    @property
    def _OAUTH_USER_INFO_URL(self):
        return "{}/v1/userinfo".format(self.base_url)

    @tornado.gen.coroutine
    def get_access_token(self, redirect_uri, code):
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
            expected_state = (self.get_secure_cookie('oauth_state') or b'').decode('utf-8')
            returned_state = self.get_argument('state')

            if returned_state is None or returned_state != expected_state:
                raise tornado.auth.AuthError(
                    'OAuth authenticator error: State tokens do not match')

            access_token_response = yield self.get_access_token(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            yield self._on_auth(access_token_response)
        else:
            state = str(uuid.uuid4())
            self.set_secure_cookie("oauth_state", state)
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['openid email'],
                response_type='code',
                extra_params={'state': state}
            )

    @tornado.gen.coroutine
    def _on_auth(self, access_token_response):
        if not access_token_response:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = access_token_response['access_token']

        response = yield self.get_auth_http_client().fetch(
            self._OAUTH_USER_INFO_URL,
            headers={'Authorization': 'Bearer ' + access_token,
                     'User-agent': 'Tornado auth'})

        decoded_body = json.loads(response.body.decode('utf-8'))
        email = (decoded_body.get('email') or '').strip()
        email_verified = (
            decoded_body.get('email_verified') and
            re.match(self.application.options.auth, email)
        )

        if not email_verified:
            message = (
                "Access denied. Please use another account or "
                "ask your admin to add your email to flower --auth."
            )
            raise tornado.web.HTTPError(403, message)

        self.set_secure_cookie("user", str(email))
        self.clear_cookie('oauth_state')

        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_
        self.redirect(next_)
