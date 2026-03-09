import base64
import datetime
import hashlib
import json
import os
import random
import re
import string
import uuid
from urllib.parse import urlencode

import tornado.auth
import tornado.gen
import tornado.web
from celery.utils.imports import instantiate
from flower.utils import strtobool
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

    @property
    def base_url(self):
        return self.application.options.oauth2_okta_base_url

    @property
    def _use_pkce(self):
        return self.application.options.oauth2_okta_enable_pkce

    @property
    def _okta_login_timeout_seconds(self):
        return self.application.options.oauth2_okta_login_timeout

    @property
    def _client_id(self):
        return self.application.options.oauth2_key

    @property
    def _client_secret(self):
        return self.application.options.oauth2_secret

    @property
    def _redirect_uri(self):
        return self.application.options.oauth2_redirect_uri

    @property
    def _OAUTH_AUTHORIZE_URL(self):
        return f"{self.base_url}/v1/authorize"

    @property
    def _OAUTH_ACCESS_TOKEN_URL(self):
        return f"{self.base_url}/v1/token"

    @property
    def _oauth_okta_scope(self):
        return self.application.options.oauth2_okta_scope.split()

    @property
    def _OAUTH_USER_INFO_URL(self):
        return f"{self.base_url}/v1/userinfo"

    async def _get_tokens(self, redirect_uri, code, pkce_code_verifier):
        url_params = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": self._client_id,
            "grant_type": "authorization_code",
        }

        if self._client_secret:
            # though not recommended for this application,
            # it's possible to not use a client secret when PKCE is enabled
            url_params["client_secret"] = self._client_secret

        if pkce_code_verifier:
            url_params["code_verifier"] = pkce_code_verifier

        body = urlencode(url_params)
        response = await self.get_auth_http_client().fetch(
            self._OAUTH_ACCESS_TOKEN_URL,
            method="POST",
            headers={'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'application/json'}, body=body)

        if response.error:
            raise tornado.auth.AuthError(f'OAuth authenticator error: {response}')

        return json.loads(response.body.decode('utf-8'))

    @staticmethod
    def _make_pkce_code_and_challenge():
        rand = random.SystemRandom()
        code_verifier = "".join(rand.choices(string.ascii_letters + string.digits, k=128))
        code_verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(code_verifier_hash).decode().rstrip("=")
        return code_verifier, code_challenge

    def _compare_state(self):
        expected_state = (self.get_secure_cookie("oauth_state") or b"").decode("utf-8")
        returned_state = self.get_argument("state")
        if returned_state is None or returned_state != expected_state:
            self._clear_oauth_cookies()
            raise tornado.auth.AuthError(
                "OAuth authenticator error: State tokens do not match")

    async def _handle_redirect(self):
        """
        Handle when user is redirected back from OKTA
        """
        pkce_code_verifier = (self.get_secure_cookie("oauth_pkce_code") or b"").decode("utf-8")
        self._compare_state()
        self._clear_oauth_cookies()

        if self._use_pkce and not pkce_code_verifier:
            raise tornado.auth.AuthError(
                "OAuth authenticator error: PKCE code verifier was not set"
            )

        tokens_response = await self._get_tokens(
            redirect_uri=self._redirect_uri,
            code=self.get_argument('code'),
            pkce_code_verifier=pkce_code_verifier,
        )
        await self._on_auth(tokens_response)

    def _set_short_lived_secure_cookie(self, name, value, **kwargs):
        """
        set a signed cookie that expires after self._okta_login_timeout_seconds
        :param name: name of the cookie
        :param value: value of the cookie
        :param kwargs: kwargs to pass into self.set_secure_cookie
        :return: None
        """
        expires = (
            datetime.datetime.now()
            + datetime.timedelta(seconds=self._okta_login_timeout_seconds)
        )
        return self.set_secure_cookie(
            name,
            value,
            expires_days=None,
            httponly=True,
            expires=expires,
        )

    async def _do_redirect(self):
        """
        Redirect user to OKTA
        """
        state = str(uuid.uuid4())
        self._set_short_lived_secure_cookie("oauth_state", state)

        extra_params = {"state": state}

        if self._use_pkce:
            code, code_challenge = self._make_pkce_code_and_challenge()
            self._set_short_lived_secure_cookie("oauth_pkce_code", code)
            extra_params.update({
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            })

        self.authorize_redirect(
            redirect_uri=self._redirect_uri,
            client_id=self._client_id,
            scope=self._oauth_okta_scope,
            response_type="code",
            extra_params=extra_params
        )

    async def _handle_oauth_error(self, error, description):
        self._compare_state()
        self._clear_oauth_cookies()
        raise tornado.web.HTTPError(403, f"OAuth failed with this error: {error}, {description}")

    async def _user_passes_test(self, user_payload):
        """
        You can override this to perform your own user testing logic
        raise a tornado.web.HTTPError if test fails (usually HTTP 403)
        return the username or email address of the user if test passes

        :param user_payload: a dictionary generated by decoding
        the response body from OKTA's OIDC userinfo endpoint
        :return: user's email address
        """
        email = (user_payload.get('email') or '').strip()
        email_verified = (
            user_payload.get('email_verified') and
            authenticate(self.application.options.auth, email)
        )

        if not email_verified:
            message = (
                "Access denied. Please use another account or "
                "ask your admin to add your email to flower --auth."
            )
            raise tornado.web.HTTPError(403, message)

        return email

    async def get(self):
        if self.get_argument("code", False):
            await self._handle_redirect()
        elif self.get_argument("error", False):
            await self._handle_oauth_error(
                error=self.get_argument("error"),
                description=self.get_argument("error_description", "")
            )
        else:
            await self._do_redirect()

    def _clear_oauth_cookies(self):
        self.clear_cookie("oauth_state")
        if self._use_pkce:
            self.clear_cookie("oauth_pkce_code")

    async def _get_userinfo(self, tokens_response):
        """
        Returns the user information in a dictionary.
        The default implementation takes the "access_token" in the token_response,
        and send it to OKTA's userinfo endpoint, and return the decoded response in a dictionary.

        You can override this to use the "id_token" and avoid sending the extra request to userinfo endpoint
        however, in that case you must validate the signature, audience and issuer of the token yourself.

        :param tokens_response: response object from OKTA's token endpoint
        :return: a dictionary containing user information
        """
        access_token = tokens_response["access_token"]
        response = await self.get_auth_http_client().fetch(
            self._OAUTH_USER_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-agent": "Tornado auth"
            }
        )

        return json.loads(response.body.decode("utf-8"))

    async def _on_auth(self, tokens_response):
        if not tokens_response:
            raise tornado.web.HTTPError(500, "OAuth authentication failed")

        userinfo = await self._get_userinfo(tokens_response)
        user = await self._user_passes_test(userinfo)
        self.set_secure_cookie("user", str(user))
        next_ = self.get_argument('next', self.application.options.url_prefix or '/')
        if self.application.options.url_prefix and next_[0] != '/':
            next_ = '/' + next_
        self.redirect(next_)
