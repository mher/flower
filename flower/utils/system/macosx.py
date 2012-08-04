from __future__ import absolute_import

import re

from .base import BaseSysInfo, call


class MacOSXSysInfo(BaseSysInfo):

    @staticmethod
    def mem_info():
        # total physical memory in bytes
        memtotal = call('sysctl -n hw.memsize')
        memtotal = int(memtotal)

        vmstat = call('vm_stat')
        size = int(re.search('\(page size of (\d*) bytes\)', vmstat).group(1))
        vmstat = dict(re.findall('\n([^:]*):\s*([0-9]*)\.', vmstat))
        memfree = int(vmstat['Pages free']) * size

        return dict(memtotal=memtotal, memfree=memfree)
