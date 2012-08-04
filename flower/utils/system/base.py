from __future__ import absolute_import

import subprocess


def call(cmd):
    if isinstance(cmd, basestring):
        cmd = cmd.split()
    return subprocess.check_output(cmd)


class BaseSysInfo(object):

    @staticmethod
    def _usage(pids=None):
        cmd = 'ps -o pid,%mem,%cpu'
        if pids:
            cmd += ' -p ' + ','.join(map(str, pids))
        stdout = call(cmd).split('\n')[1:]
        info = {}
        for line in stdout:
            if not line:
                continue
            pid, mem, cpu = line.split()
            info[int(pid)] = (float(mem), float(cpu))
        return info

    @staticmethod
    def mem_usage(pids=None):
        return {k: v[0] for k, v in BaseSysInfo._usage(pids).items()}

    @staticmethod
    def cpu_usage(pids=None):
        return {k: v[1] for k, v in BaseSysInfo._usage(pids).items()}

    @staticmethod
    def mem_info():
        raise NotImplementedError
