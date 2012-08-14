from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import SysInfoModel, WorkersModel


class SysInfo(BaseHandler):
    def get(self, workername):
        if not WorkersModel.is_worker(self.application, workername):
            raise web.HTTPError(404, "Unknown worker '%s'" % workername)
        self.write(SysInfoModel(self.application).sysinfo.get(workername, {}))
