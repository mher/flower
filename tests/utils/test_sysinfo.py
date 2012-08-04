import os
import unittest

from flower.utils.system import SysInfo


class TestSysInfo(unittest.TestCase):

    def test_mem_usage(self):
        pid = os.getpid()
        print SysInfo.mem_usage()

        self.assertIn(pid, SysInfo.mem_usage())
        self.assertIn(pid, SysInfo.mem_usage([pid]))
        self.assertEqual(1, len(SysInfo.mem_usage([pid])))
        for mem in SysInfo.mem_usage().itervalues():
            self.assertTrue(mem >= 0)
            self.assertTrue(mem < 100)

    def test_cpu_usage(self):
        pid = os.getpid()

        self.assertIn(pid, SysInfo.cpu_usage())
        self.assertIn(pid, SysInfo.cpu_usage([pid]))
        self.assertEqual(1, len(SysInfo.cpu_usage([pid])))

    def test_mem_info(self):
        self.assertIn('memtotal', SysInfo.mem_info())


if __name__ == '__main__':
    unittest.main()
