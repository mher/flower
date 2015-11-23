from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import atexit
import signal
import logging

from pprint import pformat

from tornado.options import options
from tornado.options import parse_command_line, parse_config_file
from tornado.log import enable_pretty_logging
from celery.bin.base import Command

from . import __version__
from .app import Flower
from .urls import settings
from .utils import abs_path
from .options import DEFAULT_CONFIG_FILE


logger = logging.getLogger(__name__)


class FlowerCommand(Command):
    ENV_VAR_PREFIX = 'FLOWER_'

    def run_from_argv(self, prog_name, argv=None, **_kwargs):
        env_options = filter(lambda x: x.startswith(self.ENV_VAR_PREFIX),
                             os.environ)
        for env_var_name in env_options:
            name = env_var_name.replace(self.ENV_VAR_PREFIX, '', 1).replace('_', '-').lower()
            value = os.environ[env_var_name]
            option = options._options[name]
            if option.multiple:
                value = list(map(option.type, value.split(',')))
            else:
                value = option.type(value)
            setattr(options, name, value)

        argv = list(filter(self.is_flower_option, argv))
        # parse the command line to get --conf option
        parse_command_line([prog_name] + argv)
        try:
            parse_config_file(options.conf, final=False)
            parse_command_line([prog_name] + argv)
        except IOError:
            if options.conf != DEFAULT_CONFIG_FILE:
                raise

        settings['debug'] = options.debug
        if options.cookie_secret:
            settings['cookie_secret'] = options.cookie_secret

        if options.url_prefix:
            logger.error('url_prefix option is not supported anymore')

        if options.debug and options.logging == 'info':
            options.logging = 'debug'
            enable_pretty_logging()
        else:
            logging.getLogger("tornado.access").addHandler(logging.NullHandler())
            logging.getLogger("tornado.access").propagate = False

        if options.auth:
            settings['oauth'] = {
                'key': options.oauth2_key or os.environ.get('FLOWER_OAUTH2_KEY'),
                'secret': options.oauth2_secret or os.environ.get('FLOWER_OAUTH2_SECRET'),
                'redirect_uri': options.oauth2_redirect_uri or os.environ.get('FLOWER_AUTH2_REDIRECT_URI'),
            }

        if options.certfile and options.keyfile:
            settings['ssl_options'] = dict(certfile=abs_path(options.certfile),
                                           keyfile=abs_path(options.keyfile))
            if options.ca_certs:
                settings['ssl_options']['ca_certs'] = abs_path(options.ca_certs)

        # Monkey-patch to support Celery 2.5.5
        self.app.connection = self.app.broker_connection

        self.app.loader.import_default_modules()
        flower = Flower(capp=self.app, options=options, **settings)
        atexit.register(flower.stop)

        def sigterm_handler(signal, frame):
            logger.info('SIGTERM detected, shutting down')
            sys.exit(0)
        signal.signal(signal.SIGTERM, sigterm_handler)

        self.print_banner('ssl_options' in settings)

        try:
            flower.start()
        except (KeyboardInterrupt, SystemExit):
            pass

    def handle_argv(self, prog_name, argv=None):
        return self.run_from_argv(prog_name, argv)

    def early_version(self, argv):
        if '--version' in argv:
            print(__version__, file=self.stdout)
            super(FlowerCommand, self).early_version(argv)

    @staticmethod
    def is_flower_option(arg):
        name, _, value = arg.lstrip('-').partition("=")
        name = name.replace('-', '_')
        return hasattr(options, name)

    def print_banner(self, ssl):
        logger.info(
            "Visit me at http%s://%s:%s", 's' if ssl else '',
            options.address or 'localhost', options.port
        )
        logger.info('Broker: %s', self.app.connection().as_uri())
        logger.info(
            'Registered tasks: \n%s',
            pformat(sorted(self.app.tasks.keys()))
        )
        logger.debug('Settings: %s', pformat(settings))
