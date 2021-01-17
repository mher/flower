import re
import inspect
import traceback
import copy
import logging

from distutils.util import strtobool
from base64 import b64decode

import tornado

from ..utils import template, bugreport, prepend_url

logger = logging.getLogger(__name__)


class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods',
                        ' PUT, DELETE, OPTIONS')

    def options(self):
        self.set_status(204)
        self.finish()

    def render(self, *args, **kwargs):
        app_options = self.application.options
        functions = inspect.getmembers(template, inspect.isfunction)
        assert not set(map(lambda x: x[0], functions)) & set(kwargs.keys())
        kwargs.update(functions)
        kwargs.update(url_prefix=app_options.url_prefix)
        super(BaseHandler, self).render(*args, **kwargs)

    def write_error(self, status_code, **kwargs):
        if status_code in (404, 403):
            message = ''
            if 'exc_info' in kwargs and kwargs['exc_info'][0] == tornado.web.HTTPError:
                message = kwargs['exc_info'][1].log_message
            self.render('404.html', message=message)
        elif status_code == 500:
            error_trace = ""
            for line in traceback.format_exception(*kwargs['exc_info']):
                error_trace += line

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
                message = kwargs['exc_info'][1].log_message
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
                if basic != 'Basic' or credentials not in basic_auth:
                    raise tornado.web.HTTPError(401)
            except ValueError:
                raise tornado.web.HTTPError(401)

        # OAuth2
        if not self.application.options.auth:
            return True
        user = self.get_secure_cookie('user')
        if user:
            if not isinstance(user, str):
                user = user.decode()
            if re.match(self.application.options.auth, user):
                return user
        return None

    def get_argument(self, name, default=[], strip=True, type=None):
        arg = super(BaseHandler, self).get_argument(name, default, strip)
        if arg and isinstance(arg, str):
            arg = tornado.escape.xhtml_escape(arg)
        if type is not None:
            try:
                if type is bool:
                    arg = strtobool(str(arg))
                else:
                    arg = type(arg)
            except (ValueError, TypeError):
                if arg is None and default is None:
                    return arg
                raise tornado.web.HTTPError(
                    400,
                    "Invalid argument '%s' of type '%s'" % (
                        arg, type.__name__))
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
            except:
                logger.exception("Failed to format '%s' task", task.uuid)
        return task

    def get_active_queue_names(self):
        queues = set([])
        for _, info in self.application.workers.items():
            for q in info.get('active_queues', []):
                queues.add(q['name'])
        return queues
