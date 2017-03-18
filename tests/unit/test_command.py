import os
import sys
import tempfile
import unittest
import subprocess

from flower.command import FlowerCommand
from tornado.options import options
from tests.unit import AsyncHTTPTestCase


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


class TestConfOption(AsyncHTTPTestCase):
    def test_error_conf(self):
        with self.mock_option('conf', None):
            command = FlowerCommand()
            self.assertRaises(IOError, command.apply_options,
                              'flower', argv=['--conf=foo'])
            self.assertRaises(IOError, command.apply_options,
                              'flower', argv=['--conf=/tmp/flower/foo'])

    def test_default_option(self):
        command = FlowerCommand()
        command.apply_options('flower', argv=[])
        self.assertEqual('flowerconfig.py', options.conf)

    def test_empty_conf(self):
        with self.mock_option('conf', None):
            command = FlowerCommand()
            command.apply_options('flower', argv=['--conf=/dev/null'])
            self.assertEqual('/dev/null', options.conf)

    def test_conf_abs(self):
        with tempfile.NamedTemporaryFile() as cf:
            with self.mock_option('conf', cf.name), self.mock_option('debug', False):
                cf.write('debug=True\n'.encode('utf-8'))
                cf.flush()
                command = FlowerCommand()
                command.apply_options('flower', argv=['--conf=%s' % cf.name])
                self.assertEqual(cf.name, options.conf)
                self.assertTrue(options.debug)

    def test_conf_relative(self):
        with tempfile.NamedTemporaryFile(dir='.') as cf:
            with self.mock_option('conf', cf.name), self.mock_option('debug', False):
                cf.write('debug=True\n'.encode('utf-8'))
                cf.flush()
                command = FlowerCommand()
                command.apply_options('flower', argv=['--conf=%s' % os.path.basename(cf.name)])
                self.assertTrue(options.debug)

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
