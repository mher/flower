import sys
import unittest
import subprocess

from flower.command import FlowerCommand
from tornado.options import options
from tests import AsyncHTTPTestCase


# python 2.6 support
if not hasattr(unittest, 'skipUnless'):
    import unittest2 as unittest


class TestFlowerCommand(AsyncHTTPTestCase):
    def test_port(self):
        with self.mock_option('port', 5555):
            command = FlowerCommand()
            command.apply_options('flower', argv=['--port=123'])
            self.assertEqual(123, options.port)

    def test_address(self):
        with self.mock_option('address', '127.0.0.1'):
            command = FlowerCommand()
            command.apply_options('flower', argv=['--address=foo'])
            self.assertEqual('foo', options.address)

    def test_conf(self):
        with self.mock_option('conf', None):
            command = FlowerCommand()
            self.assertRaises(IOError, command.apply_options,
                              'flower', argv=['--conf=foo'])

    @unittest.skipUnless(not sys.platform.startswith("win"), 'skip windows')
    @unittest.skipUnless(sys.version_info[:2] > (2, 6), 'skip python 2.6')
    def test_all_options_documented(self):
        def grep(patter, filename):
            return int(subprocess.check_output(
                'grep "%s" %s|wc -l' % (patter, filename), shell=True))

        defined = grep('^define(', 'flower/options.py') - 4
        documented = grep('^~~', 'docs/config.rst')
        self.assertEqual(defined, documented,
                msg='Missing option documentation. Make sure all options '
                    'are documented in docs/config.rst')
