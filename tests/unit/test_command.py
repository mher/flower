import os
import sys
import tempfile
import unittest
import subprocess
from unittest.mock import Mock, patch, create_autospec, MagicMock

import mock
from celery import Celery
from kombu.exceptions import OperationalError

from flower.command import apply_options, warn_about_celery_args_used_in_flower_command, is_broker_connected
from tornado.options import options
from tests.unit import AsyncHTTPTestCase


class TestFlowerCommand(AsyncHTTPTestCase):
    def test_port(self):
        with self.mock_option('port', 5555):
            apply_options('flower', argv=['--port=123'])
            self.assertEqual(123, options.port)

    def test_address(self):
        with self.mock_option('address', '127.0.0.1'):
            apply_options('flower', argv=['--address=foo'])
            self.assertEqual('foo', options.address)

    def test_autodiscovery(self):
        """
        Simulate basic Django setup:
        - creating celery app
        - run app.autodiscover_tasks()
        - create flower command
        """
        celery_app = self._get_celery_app()
        with mock.patch.object(celery_app, '_autodiscover_tasks') as autodiscover:
            celery_app.autodiscover_tasks()

            self.get_app(capp=celery_app)

            self.assertTrue(autodiscover.called)


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
            "[\'--app\', \'-b\']. Please specify them after celery command instead following"
            " this template: celery [celery args] flower [flower args]."
        )


class TestIsBrokerConnected(AsyncHTTPTestCase):
    @patch('flower.command.logger.info')
    def test_returns_true_and_logs_if_connection_to_broker_established(self, mock_info):
        broker_url = 'broker_url'
        broker_connection_max_retries = 2

        mock_conf = Mock(broker_connection_retry=True, broker_connection_max_retries=broker_connection_max_retries)

        mock_connection = MagicMock(name='mock connection')
        mock_connection.as_uri.return_value = broker_url
        mock_connection.__enter__.return_value = mock_connection

        mock_celery_app = create_autospec(Celery, conf=mock_conf)
        mock_celery_app.connection.return_value = mock_connection

        assert is_broker_connected(celery_app=mock_celery_app)

        mock_connection.ensure_connection.assert_called_once()
        ensure_connection_kwargs = mock_connection.ensure_connection.call_args_list[0].kwargs
        assert '_error_handler' in str(ensure_connection_kwargs['errback'])
        assert ensure_connection_kwargs['max_retries'] == broker_connection_max_retries

        mock_info.assert_called_once_with(f'Established connection to broker: {broker_url}. Starting Flower...')

    @patch('flower.command.logger.error')
    def test_returns_false_and_logs_error_if_connection_to_broker_cannot_be_established(self, mock_error):
        broker_url = 'broker_url'
        broker_connection_max_retries = 2

        mock_conf = Mock(broker_connection_retry=True, broker_connection_max_retries=broker_connection_max_retries)

        mock_connection = MagicMock(name='mock connection')
        mock_connection.as_uri.return_value = broker_url
        error = OperationalError('test error')
        mock_connection.ensure_connection.side_effect = error
        mock_connection.__enter__.return_value = mock_connection

        mock_celery_app = create_autospec(Celery, conf=mock_conf)
        mock_celery_app.connection.return_value = mock_connection

        assert not is_broker_connected(celery_app=mock_celery_app)

        mock_connection.ensure_connection.assert_called_once()
        ensure_connection_kwargs = mock_connection.ensure_connection.call_args_list[0].kwargs
        assert '_error_handler' in str(ensure_connection_kwargs['errback'])
        assert ensure_connection_kwargs['max_retries'] == broker_connection_max_retries

        mock_error.assert_called_once_with(
            f'Unable to establish connection to broker: : {broker_url}. Error: {error}. '
            f'Please make sure the broker is running when using Flower. Aborting Flower...'
        )

    @patch('flower.command.logger.error')
    def test_disabled_broker_connection_retry_sets_max_retries_to_zero(self, mock_error):
        broker_url = 'broker_url'
        broker_connection_max_retries = 2

        mock_conf = Mock(broker_connection_retry=False, broker_connection_max_retries=broker_connection_max_retries)

        mock_connection = MagicMock(name='mock connection')
        mock_connection.as_uri.return_value = broker_url
        mock_connection.__enter__.return_value = mock_connection

        mock_celery_app = create_autospec(Celery, conf=mock_conf)
        mock_celery_app.connection.return_value = mock_connection

        assert is_broker_connected(celery_app=mock_celery_app)

        mock_connection.ensure_connection.assert_called_once()
        ensure_connection_kwargs = mock_connection.ensure_connection.call_args_list[0].kwargs
        assert '_error_handler' in str(ensure_connection_kwargs['errback'])
        assert ensure_connection_kwargs['max_retries'] == 0


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

        defined = grep('^define(', 'flower/options.py') - 4
        documented = grep('^~~', 'docs/config.rst')
        self.assertEqual(defined, documented,
                         msg='Missing option documentation. Make sure all options '
                             'are documented in docs/config.rst')
