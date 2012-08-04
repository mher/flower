from __future__ import absolute_import

from ..views import BaseHandler
from ..models import SysInfoModel


class SystemView(BaseHandler):
    def get(self):
        sysinfo = {}
        for i in SysInfoModel().sysinfo:
            sysinfo.update(i)
        self.render("system.html", sysinfo=sysinfo)
