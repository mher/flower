from __future__ import absolute_import

import re
import inspect
import traceback

from urlparse import urljoin
from base64 import b64decode

import tornado

from .. import settings
from ..utils import template, bugreport


class BaseHandler(tornado.web.RequestHandler):

    def prepare(self):
        self.application.state.resume()

    def render(self, *args, **kwargs):
        functions = inspect.getmembers(template, inspect.isfunction)
        assert not set(map(lambda x: x[0], functions)) & set(kwargs.iterkeys())
        kwargs.update(functions)
        kwargs.update(absolute_url=self.absolute_url)
        kwargs.update(url_prefix=settings.URL_PREFIX)
        super(BaseHandler, self).render(*args, **kwargs)

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            message = None
            if 'exc_info' in kwargs and\
                    kwargs['exc_info'][0] == tornado.web.HTTPError:
                    message = kwargs['exc_info'][1].log_message
            self.render('404.html', message=message)
        elif status_code == 500:
            error_trace = ""
            for line in traceback.format_exception(*kwargs['exc_info']):
                error_trace += line

            self.render('error.html',
                        status_code=status_code,
                        error_trace=error_trace,
                        bugreport=bugreport())
        elif status_code == 401:
            self.set_status(status_code)
            self.set_header('WWW-Authenticate', 'Basic realm="flower"')
            self.finish('Access denied')
        else:
            message = None
            if 'exc_info' in kwargs and\
                    kwargs['exc_info'][0] == tornado.web.HTTPError:
                    message = kwargs['exc_info'][1].log_message
                    self.set_header('Content-Type', 'text/plain')
                    self.write(message)
            self.set_status(status_code)

    def get_current_user(self):
        # Basic Auth
        basic_auth = self.application.basic_auth
        if basic_auth:
            auth_header = self.request.headers.get("Authorization", "")
            try:
                basic, credentials = auth_header.split()
                credentials = b64decode(credentials)
                if basic != 'Basic' or credentials != basic_auth:
                    raise tornado.web.HTTPError(401)
            except ValueError:
                raise tornado.web.HTTPError(401)

        # Google OpenID
        if not self.application.auth:
            return True
        user = self.get_secure_cookie('user')
        if user and re.search(self.application.auth, user):
            return user
        else:
            return

    def absolute_url(self, url):
        base = "{0}://{1}/".format(self.request.protocol, self.request.host)
        if settings.URL_PREFIX:
            base += settings.URL_PREFIX + '/'
        aurl = urljoin(base, url[1:] if url.startswith('/') else url)
        aurl = aurl[:-1] if aurl.endswith('/') else aurl
        return aurl
