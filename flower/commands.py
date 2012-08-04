"""Remote control commands for Celery"""
from __future__ import absolute_import

import os

from celery.worker.control import Panel

from .utils.system import SysInfo


@Panel.register
def cpu_usage(panel):
    pids = [p.pid for p in panel.consumer.pool._pool._pool]
    pids.append(os.getpid())
    return SysInfo.cpu_usage(pids)


@Panel.register
def mem_usage(panel):
    pids = [p.pid for p in panel.consumer.pool._pool._pool]
    pids.append(os.getpid())
    return SysInfo.mem_usage(pids)


@Panel.register
def mem_info(panel):
    return SysInfo.mem_info()


@Panel.register
def sysinfo(panel):
    pids = [p.pid for p in panel.consumer.pool._pool._pool]
    pids.append(os.getpid())
    return dict(memusage=SysInfo.mem_usage(pids),
                memtotal=SysInfo.mem_info()['memtotal'],
                cpuusage=SysInfo.cpu_usage(pids))
