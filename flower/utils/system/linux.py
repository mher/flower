from __future__ import absolute_import
from __future__ import with_statement

from .base import BaseSysInfo


class LinuxSysInfo(BaseSysInfo):

    @staticmethod
    def mem_info():
        with open('/proc/meminfo') as mf:
            info = {}
            for line in mf:
                name, value, unit = line.split()
                name = name.rstrip(':').lower()
                assert unit.lower() == 'kb'
                if name in ('memtotal', 'memfree'):
                    info[name] = int(value) * 1024
            return info
