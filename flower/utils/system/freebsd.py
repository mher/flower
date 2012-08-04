from __future__ import absolute_import

from .base import BaseSysInfo, call


class FreeBSDSysInfo(BaseSysInfo):

    @staticmethod
    def mem_info():
        memtotal = call('sysctl -n hw.realmem')
        memtotal = int(memtotal)
        return dict(memtotal=memtotal)
