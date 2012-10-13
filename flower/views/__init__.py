from __future__ import absolute_import

import inspect
import traceback

import tornado

from ..utils import template


class BaseHandler(tornado.web.RequestHandler):
    def render(self, *args, **kwargs):
        functions = inspect.getmembers(template, inspect.isfunction)
        assert not set(map(lambda x: x[0], functions)) & set(kwargs.iterkeys())
        kwargs.update(functions)
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
                        error_trace=error_trace)
        else:
            message = None
            if 'exc_info' in kwargs and\
                kwargs['exc_info'][0] == tornado.web.HTTPError:
                    message = kwargs['exc_info'][1].log_message
                    self.set_header('Content-Type', 'text/plain')
                    self.write(message)
            self.set_status(status_code)

    def get_current_user(self):
        if not self.application.auth:
            return True
        user = self.get_secure_cookie('user')
        if user and user in self.application.auth:
            return user
        else:
            return None
