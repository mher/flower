import copy
import hmac
import inspect
import logging
import os
import traceback
from base64 import b64decode
from urllib.parse import urlparse

import tornado
import tornado.auth

from ..utils import bugreport, strtobool, template
from ..utils.authentication import authenticate
from ..utils.broker import Broker

logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def unauthenticated_api(self):
        return strtobool(os.environ.get('FLOWER_UNAUTHENTICATED_API') or 'false')

    def set_default_headers(self):
        self.set_header('X-Content-Type-Options', 'nosniff')
        options = self.application.options
        # Cross-origin reads are only for instances explicitly opened to unauthenticated clients
        if not (options.basic_auth or options.auth) and self.unauthenticated_api:
            self.set_header("Access-Control-Allow-Origin", "*")
            self.set_header("Access-Control-Allow-Headers",
                            "x-requested-with,access-control-allow-origin,authorization,content-type")
            self.set_header('Access-Control-Allow-Methods',
                            ' PUT, DELETE, OPTIONS, POST, GET, PATCH')

    def options(self, *_, **__):
        self.set_status(204)
    def _resolve_asset_url(self, asset, asset_type):
        if not asset:
            return None
        if asset.startswith(('http://', 'https://', '//', 'data:')):
            return asset
        if os.path.isfile(asset):
            prefix = getattr(self.application.options, 'url_prefix', None)
            endpoint = f"/custom-asset/{asset_type}"
            if prefix:
                endpoint = f"/{prefix.strip('/')}{endpoint}"
            return endpoint
        if asset.startswith('/'):
            prefix = getattr(self.application.options, 'url_prefix', None)
            if prefix and not asset.startswith(f"/{prefix.strip('/')}/"):
                return f"/{prefix.strip('/')}{asset}"
            return asset
        return asset

    def get_template_namespace(self):
        namespace = super().get_template_namespace()
        app_options = self.application.options
        functions = dict(inspect.getmembers(template, inspect.isfunction))
        namespace.update(functions)
        namespace.update(
            url_prefix=getattr(app_options, 'url_prefix', None),
            app_name=getattr(app_options, 'app_name', 'Flower'),
            brand_logo=self._resolve_asset_url(getattr(app_options, 'brand_logo', None), 'logo'),
            brand_favicon=self._resolve_asset_url(getattr(app_options, 'brand_favicon', None), 'favicon'),
            custom_css=self._resolve_asset_url(getattr(app_options, 'custom_css', None), 'css'),
            primary_color=getattr(app_options, 'primary_color', None),
            secondary_color=getattr(app_options, 'secondary_color', None),
        )
        return namespace

    def render(self, *args, **kwargs):
        # Set the _xsrf cookie so the UI's AJAX calls can echo the token back
        _ = self.xsrf_token
        super().render(*args, **kwargs)

    def check_xsrf_cookie(self):
        options = self.application.options
        site = self.request.headers.get('Sec-Fetch-Site')
        origin = self.request.headers.get('Origin')

        # No authentication configured
        if not (options.basic_auth or options.auth):
            return

        # Cross-site request
        if site and site != 'same-origin':
            raise tornado.web.HTTPError(403, 'Cross-site request forbidden')

        # Mismatched origin, no fetch metadata
        if not site and origin and urlparse(origin).netloc != self.request.host:
            raise tornado.web.HTTPError(403, 'Cross-origin request forbidden')

        # Basic auth, no cookie session
        if not options.auth:
            return

        # Token client, no cookie session
        if self.request.headers.get('Authorization'):
            return

        super().check_xsrf_cookie()

    def set_secure_cookie(self, name, value, expires_days=30, version=None, **kwargs):
        kwargs.setdefault('httponly', True)
        kwargs.setdefault('samesite', 'Lax')
        super().set_secure_cookie(name, value, expires_days, version, **kwargs)

    def log_exception(self, typ, value, tb):
        # OAuth failures are user errors, not server faults
        if isinstance(value, tornado.auth.AuthError):
            logger.warning("Authentication error: %s", value)
            return
        super().log_exception(typ, value, tb)

    def write_error(self, status_code, **kwargs):
        # Avoid re-running authentication while rendering an error response
        if not hasattr(self, '_current_user'):
            self.current_user = None

        exc_info = kwargs.get('exc_info')
        if exc_info and isinstance(exc_info[1], tornado.auth.AuthError):
            self.set_status(403)
            self.render('404.html',
                        message=f'{exc_info[1]}. Please try logging in again.')
            return

        if status_code in (404, 403):
            message = ''
            if 'exc_info' in kwargs and kwargs['exc_info'][0] == tornado.web.HTTPError:
                message = kwargs['exc_info'][1].get_message()
            self.render('404.html', message=message)
        elif status_code == 500:
            error_trace = "".join(traceback.format_exception(*kwargs['exc_info']))

            self.render('error.html',
                    debug=self.application.options.debug,
                    status_code=status_code,
                    error_trace=error_trace,
                    bugreport=bugreport())
        elif status_code == 401:
            self.set_status(status_code)
            self.set_header('WWW-Authenticate', 'Basic realm="flower"')
            self.finish('Access denied')
        else:
            message = ''
            if 'exc_info' in kwargs and kwargs['exc_info'][0] == tornado.web.HTTPError:
                message = kwargs['exc_info'][1].get_message()
                self.set_header('Content-Type', 'text/plain')
                self.write(str(message))
            self.set_status(status_code)
            self.finish()

    def get_current_user(self):
        # Basic Auth
        basic_auth = self.application.options.basic_auth
        if basic_auth:
            auth_header = self.request.headers.get("Authorization", "")
            try:
                basic, credentials = auth_header.split()
                credentials = b64decode(credentials.encode()).decode()
                if basic != 'Basic':
                    raise tornado.web.HTTPError(401)
                for stored_credential in basic_auth:
                    if hmac.compare_digest(stored_credential, credentials):
                        break
                else:
                    raise tornado.web.HTTPError(401)
            except ValueError as exc:
                raise tornado.web.HTTPError(401) from exc

        # OAuth2
        if not self.application.options.auth:
            return True
        user = self.get_secure_cookie('user')
        if user:
            if not isinstance(user, str):
                user = user.decode()
            if authenticate(self.application.options.auth, user):
                return user
        return None

    # pylint: disable=too-many-arguments
    def get_argument(self, name, default=None, strip=True, type=None,
                     required=False, escape=True):
        arg = super().get_argument(name, default, strip)
        if required and (arg is None or arg == ''):
            raise tornado.web.HTTPError(400, f"Missing argument {name}")
        # Values that are only parsed, like search queries, must keep quotes and brackets
        if escape and arg and isinstance(arg, str):
            arg = tornado.escape.xhtml_escape(arg)
        if type is not None:
            try:
                if type is bool:
                    arg = strtobool(str(arg))
                else:
                    arg = type(arg)
            except (ValueError, TypeError) as exc:
                if arg is None and default is None:
                    return arg
                raise tornado.web.HTTPError(
                        400,
                        f"Invalid argument '{arg}' of type '{type.__name__}'") from exc
        return arg

    @property
    def capp(self):
        "return Celery application object"
        return self.application.capp

    def format_task(self, task):
        custom_format_task = self.application.options.format_task
        if custom_format_task:
            try:
                task = custom_format_task(copy.copy(task))
            except Exception:
                logger.exception("Failed to format '%s' task", task.uuid)
        return task

    def get_broker(self):
        app = self.application
        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api
        try:
            return Broker(app.broker_uri_with_password, http_api=http_api,
                          broker_options=self.capp.conf.broker_transport_options,
                          broker_use_ssl=self.capp.conf.broker_use_ssl)
        except NotImplementedError as exc:
            raise tornado.web.HTTPError(
                404, f"'{app.transport}' broker is not supported") from exc

    def get_active_queue_names(self):
        queues = set()
        for info in self.application.workers.values():
            for queue in info.get('active_queues', []):
                queues.add(queue['name'])

        if not queues:
            queues = {self.capp.conf.task_default_queue} |\
                {q.name for q in self.capp.conf.task_queues or [] if q.name}
        return sorted(queues)
