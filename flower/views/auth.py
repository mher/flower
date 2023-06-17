import json
import os
import re
import uuid
from urllib.parse import urlencode

import tornado.auth
import tornado.gen
import tornado.web
from celery.utils.imports import instantiate
from tornado.options import options

from ..views import BaseHandler
from ..views.error import NotFoundErrorHandler

# pylint: disable=invalid-name


def authenticate(pattern, email):
    if '|' in pattern:
        return email in pattern.split('|')
    if '*' in pattern:
        pattern = re.escape(pattern).replace(r'\.\*', r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.\-]*")
        return re.fullmatch(pattern, email)
    return pattern == email


def validate_auth_option(pattern):
    if pattern.count('*') > 1:
        return False
    if '*' in pattern and '|' in pattern:
        return False
    if '*' in pattern.rsplit('@', 1)[-1]:
        return False
    return True


class GoogleAuth2LoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    _OAUTH_SETTINGS_KEY = 'oauth'

    async def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            user = await self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            await self._on_auth(user)
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': ''}
            )

    async def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(403, 'Google auth failed')
        access_token = user['access_token']

        try:
            response = await self.get_auth_http_client().fetch(
                'https://www.googleapis.com/userinfo/v2/me',
                headers={'Authorization': f'Bearer {access_token}'})
        except Exception as e:
            raise tornado.web.HTTPError(403, f'Google auth failed: {e}')

        email = json.loads(response.body.decode('utf-8'))['email']
        if not authenticate(self.application.options.auth, email):
            message = f"Access denied to '{email}'. Please use another account or ask your admin to add your email to flower --auth."
            raise tornado.web.HTTPError(403, message)

        self.set_secure_cookie("user", str(email))

        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_

        self.redirect(next_)


class LoginHandler(BaseHandler):
    def __new__(cls, *args, **kwargs):
        return instantiate(options.auth_provider or NotFoundErrorHandler, *args, **kwargs)


class GithubLoginHandler(BaseHandler, tornado.auth.OAuth2Mixin):

    _OAUTH_DOMAIN = os.getenv(
        "FLOWER_GITHUB_OAUTH_DOMAIN", "github.com")
    _OAUTH_AUTHORIZE_URL = f'https://{_OAUTH_DOMAIN}/login/oauth/authorize'
    _OAUTH_ACCESS_TOKEN_URL = f'https://{_OAUTH_DOMAIN}/login/oauth/access_token'
    _OAUTH_NO_CALLBACKS = False
    _OAUTH_SETTINGS_KEY = 'oauth'

    async def get_authenticated_user(self, redirect_uri, code):
        body = urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]['secret'],
            "grant_type": "authorization_code",
        })

        response = await self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'}, body=body)

        if response.error:
            raise tornado.auth.AuthError(f'OAuth authenticator error: {response}')

        return json.loads(response.body.decode('utf-8'))

    async def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            user = await self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            await self._on_auth(user)
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['user:email'],
                response_type='code',
                extra_params={'approval_prompt': ''}
            )

    async def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = user['access_token']

        response = await self.get_auth_http_client().fetch(
            f'https://api.{self._OAUTH_DOMAIN}/user/emails',
            headers={'Authorization': 'token ' + access_token,
                     'User-agent': 'Tornado auth'})

        emails = [email['email'].lower() for email in json.loads(response.body.decode('utf-8'))
                  if email['verified'] and authenticate(self.application.options.auth, email['email'])]

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

    _OAUTH_GITLAB_DOMAIN = os.getenv(
        "FLOWER_GITLAB_OAUTH_DOMAIN", "gitlab.com")
    _OAUTH_AUTHORIZE_URL = f'https://{_OAUTH_GITLAB_DOMAIN}/oauth/authorize'
    _OAUTH_ACCESS_TOKEN_URL = f'https://{_OAUTH_GITLAB_DOMAIN}/oauth/token'
    _OAUTH_NO_CALLBACKS = False

    async def get_authenticated_user(self, redirect_uri, code):
        body = urlencode({
            'redirect_uri': redirect_uri,
            'code': code,
            'client_id': self.settings['oauth']['key'],
            'client_secret': self.settings['oauth']['secret'],
            'grant_type': 'authorization_code',
        })
        response = await self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'},
            body=body
        )
        if response.error:
            raise tornado.auth.AuthError(f'OAuth authenticator error: {response}')
        return json.loads(response.body.decode('utf-8'))

    async def get(self):
        redirect_uri = self.settings['oauth']['redirect_uri']
        if self.get_argument('code', False):
            user = await self.get_authenticated_user(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            await self._on_auth(user)
        else:
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings['oauth']['key'],
                scope=['read_api'],
                response_type='code',
                extra_params={'approval_prompt': ''},
            )

    async def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = user['access_token']
        allowed_groups = os.environ.get('FLOWER_GITLAB_AUTH_ALLOWED_GROUPS', '')
        allowed_groups = [group.strip() for group in allowed_groups.split(',') if group]

        # Check user email address against regexp
        try:
            response = await self.get_auth_http_client().fetch(
                f'https://{self._OAUTH_GITLAB_DOMAIN}/api/v4/user',
                headers={'Authorization': 'Bearer ' + access_token,
                         'User-agent': 'Tornado auth'}
            )
        except Exception as e:
            raise tornado.web.HTTPError(403, f'GitLab auth failed: {e}')

        user_email = json.loads(response.body.decode('utf-8'))['email']
        email_allowed = authenticate(self.application.options.auth, user_email)

        # Check user's groups against list of allowed groups
        matching_groups = []
        if allowed_groups:
            min_access_level = os.environ.get('FLOWER_GITLAB_MIN_ACCESS_LEVEL', '20')
            response = await self.get_auth_http_client().fetch(
                f'https://{self._OAUTH_GITLAB_DOMAIN}/api/v4/groups?min_access_level={min_access_level}',
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
        return f"{self.base_url}/v1/authorize"

    @property
    def _OAUTH_ACCESS_TOKEN_URL(self):
        return f"{self.base_url}/v1/token"

    @property
    def _OAUTH_USER_INFO_URL(self):
        return f"{self.base_url}/v1/userinfo"

    async def get_access_token(self, redirect_uri, code):
        body = urlencode({
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self.settings[self._OAUTH_SETTINGS_KEY]['key'],
            "client_secret": self.settings[self._OAUTH_SETTINGS_KEY]['secret'],
            "grant_type": "authorization_code",
        })

        response = await self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'}, body=body)

        if response.error:
            raise tornado.auth.AuthError(f'OAuth authenticator error: {response}')

        return json.loads(response.body.decode('utf-8'))

    async def get(self):
        redirect_uri = self.settings[self._OAUTH_SETTINGS_KEY]['redirect_uri']
        if self.get_argument('code', False):
            expected_state = (self.get_secure_cookie('oauth_state') or b'').decode('utf-8')
            returned_state = self.get_argument('state')

            if returned_state is None or returned_state != expected_state:
                raise tornado.auth.AuthError(
                    'OAuth authenticator error: State tokens do not match')

            access_token_response = await self.get_access_token(
                redirect_uri=redirect_uri,
                code=self.get_argument('code'),
            )
            await self._on_auth(access_token_response)
        else:
            state = str(uuid.uuid4())
            self.set_secure_cookie("oauth_state", state)
            self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings[self._OAUTH_SETTINGS_KEY]['key'],
                scope=['openid email'],
                response_type='code',
                extra_params={'state': state}
            )

    async def _on_auth(self, access_token_response):
        if not access_token_response:
            raise tornado.web.HTTPError(500, 'OAuth authentication failed')
        access_token = access_token_response['access_token']

        response = await self.get_auth_http_client().fetch(
            self._OAUTH_USER_INFO_URL,
            headers={'Authorization': 'Bearer ' + access_token,
                     'User-agent': 'Tornado auth'})

        decoded_body = json.loads(response.body.decode('utf-8'))
        email = (decoded_body.get('email') or '').strip()
        email_verified = (
            decoded_body.get('email_verified') and
            authenticate(self.application.options.auth, email)
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
