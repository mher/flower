import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import celery
from prometheus_client import Histogram
from tornado.options import options

from flower.command import (apply_env_options, apply_options, print_banner,
                            warn_about_celery_args_used_in_flower_command)
from tests.unit import AsyncHTTPTestCase


class TestFlowerCommand(AsyncHTTPTestCase):
    def test_task_runtime_metric_buckets_read_from_cmd_line(self):
        apply_options('flower', argv=['--task_runtime_metric_buckets=1,10,inf'])
        self.assertEqual([1.0, 10.0, float('inf')], options.task_runtime_metric_buckets)

    def test_task_runtime_metric_buckets_no_cmd_line_arg(self):
        apply_options('flower', argv=[])
        self.assertEqual(Histogram.DEFAULT_BUCKETS, options.task_runtime_metric_buckets)

    def test_task_runtime_metric_buckets_read_from_env(self):
        with patch.dict(os.environ, {"FLOWER_TASK_RUNTIME_METRIC_BUCKETS": "2,5,inf"}):
            apply_env_options()
            self.assertEqual([2.0, 5.0, float('inf')], options.task_runtime_metric_buckets)

    def test_task_runtime_metric_buckets_no_env_value_provided(self):
        apply_env_options()
        self.assertEqual(Histogram.DEFAULT_BUCKETS, options.task_runtime_metric_buckets)

    def test_port(self):
        with self.mock_option('port', 5555):
            apply_options('flower', argv=['--port=123'])
            self.assertEqual(123, options.port)

    def test_address(self):
        with self.mock_option('address', '127.0.0.1'):
            apply_options('flower', argv=['--address=foo'])
            self.assertEqual('foo', options.address)

    def test_auto_refresh(self):
        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "false"}):
            apply_env_options()
            self.assertFalse(options.auto_refresh)

        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "true"}):
            apply_env_options()
            self.assertTrue(options.auto_refresh)

        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "0"}):
            apply_env_options()
            self.assertFalse(options.auto_refresh)

        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "1"}):
            apply_env_options()
            self.assertTrue(options.auto_refresh)

        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "False"}):
            apply_env_options()
            self.assertFalse(options.auto_refresh)

        with patch.dict(os.environ, {"FLOWER_AUTO_REFRESH": "True"}):
            apply_env_options()
            self.assertTrue(options.auto_refresh)

    def test_autodiscovery(self):
        """
        Simulate basic Django setup:
        - creating celery app
        - run app.autodiscover_tasks()
        - create flower command
        """
        celery_app = self._get_celery_app()
        with patch.object(celery_app, '_autodiscover_tasks') as autodiscover:
            celery_app.autodiscover_tasks()

            self.get_app(capp=celery_app)

            self.assertTrue(autodiscover.called)


class TestPrintBanner(AsyncHTTPTestCase):
    def test_print_banner(self):
        celery_app = celery.Celery()
        with self.assertLogs('', level='INFO') as cm:
            print_banner(celery_app, False)

            self.assertTrue('INFO:flower.command:Visit me at http://0.0.0.0:5555' in cm.output)
            self.assertTrue('INFO:flower.command:Broker: amqp://guest:**@localhost:5672//' in cm.output)

    def test_print_banner_with_ssl(self):
        celery_app = celery.Celery()
        with self.assertLogs('', level='INFO') as cm:
            print_banner(celery_app, True)

            self.assertTrue('INFO:flower.command:Visit me at https://0.0.0.0:5555' in cm.output)
            self.assertTrue('INFO:flower.command:Broker: amqp://guest:**@localhost:5672//' in cm.output)

    def test_print_banner_unix_socket(self):
        celery_app = celery.Celery()
        with self.assertLogs('', level='INFO') as cm, self.mock_option('unix_socket', 'foo'):
            print_banner(celery_app, True)

            self.assertTrue('INFO:flower.command:Visit me via unix socket file: foo' in cm.output)


class TestWarnAboutCeleryArgsUsedInFlowerCommand(AsyncHTTPTestCase):
    @patch('flower.command.logger.warning')
    def test_does_not_log_warning(self, mock_warning):
        mock_app_param = Mock(name='app_param', opts=('-A', '--app'))
        mock_broker_param = Mock(name='broker_param', opts=('-b', '--broker'))

        class FakeContext:
            parent = Mock(command=Mock(params=[mock_app_param, mock_broker_param]))

        ctx = FakeContext()

        warn_about_celery_args_used_in_flower_command(
            ctx=ctx, flower_args=('--port=5678', '--address=0.0.0.0')
        )

        mock_warning.assert_not_called()

    @patch('flower.command.logger.warning')
    def test_logs_warning(self, mock_warning):
        mock_app_param = Mock(name='app_param', opts=('-A', '--app'))
        mock_broker_param = Mock(name='broker_param', opts=('-b', '--broker'))

        class FakeContext:
            parent = Mock(command=Mock(params=[mock_app_param, mock_broker_param]))

        ctx = FakeContext()

        warn_about_celery_args_used_in_flower_command(
            ctx=ctx, flower_args=('--app=proj', '-b', 'redis://localhost:6379/0')
        )

        mock_warning.assert_called_once_with(
            "You have incorrectly specified the following celery arguments after flower command: "
            "%s. Please specify them after celery command instead following"
            " this template: celery [celery args] flower [flower args].", ['--app', '-b']
        )


class TestConfOption(AsyncHTTPTestCase):
    def test_error_conf(self):
        with self.mock_option('conf', None):
            self.assertRaises(IOError, apply_options,
                              'flower', argv=['--conf=foo'])
            self.assertRaises(IOError, apply_options,
                              'flower', argv=['--conf=/tmp/flower/foo'])

    def test_default_option(self):
        apply_options('flower', argv=[])
        self.assertEqual('flowerconfig.py', options.conf)

    def test_empty_conf(self):
        with self.mock_option('conf', None):
            apply_options('flower', argv=['--conf=/dev/null'])
            self.assertEqual('/dev/null', options.conf)

    def test_conf_abs(self):
        with tempfile.NamedTemporaryFile() as cf:
            with self.mock_option('conf', cf.name), self.mock_option('debug', False):
                cf.write('debug=True\n'.encode('utf-8'))
                cf.flush()
                apply_options('flower', argv=['--conf=%s' % cf.name])
                self.assertEqual(cf.name, options.conf)
                self.assertTrue(options.debug)

    def test_conf_relative(self):
        with tempfile.NamedTemporaryFile(dir='.') as cf:
            with self.mock_option('conf', cf.name), self.mock_option('debug', False):
                cf.write('debug=True\n'.encode('utf-8'))
                cf.flush()
                apply_options('flower', argv=['--conf=%s' % os.path.basename(cf.name)])
                self.assertTrue(options.debug)

    @unittest.skipUnless(not sys.platform.startswith("win"), 'skip windows')
    def test_all_options_documented(self):
        def grep(patter, filename):
            return int(subprocess.check_output(
                'grep "%s" %s|wc -l' % (patter, filename), shell=True))

        defined = grep('^define(', 'flower/options.py')
        documented = grep('^~~', 'docs/config.rst')
        self.assertEqual(defined, documented,
                         msg='Missing option documentation. Make sure all options '
                             'are documented in docs/config.rst')
