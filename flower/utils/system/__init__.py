from __future__ import absolute_import

import sys


if sys.platform.startswith('freebsd'):
    from .freebsd import FreeBSDSysInfo
    SysInfo = FreeBSDSysInfo
elif sys.platform.startswith('linux'):
    from .linux import LinuxSysInfo
    SysInfo = LinuxSysInfo
elif sys.platform.startswith('darwin'):
    from .macosx import MacOSXSysInfo
    SysInfo = MacOSXSysInfo
else:
    raise Exception("Unsupported platform '%s'" % sys.platform)
