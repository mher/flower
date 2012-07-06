from __future__ import absolute_import

import inspect

import tornado

from ..utils import template


class BaseHandler(tornado.web.RequestHandler):
    def render(self, *args, **kwargs):
        functions = inspect.getmembers(template, inspect.isfunction)
        assert not set(map(lambda x: x[0], functions)) & set(kwargs.iterkeys())
        kwargs.update(functions)
        super(BaseHandler, self).render(*args, **kwargs)
