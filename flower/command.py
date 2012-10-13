from __future__ import absolute_import

import logging

from pprint import pformat

from tornado.options import define, options, parse_command_line

from celery.bin.base import Command

from . import settings
from .app import Flower

define("port", default=5555, help="run on the given port", type=int)
define("address", default='', help="run on the given address", type=str)
define("debug", default=False, help="run in debug mode", type=bool)
define("inspect", default=True, help="inspect workers", type=bool)
define("inspect_timeout", default=1000, type=float,
        help="inspect timeout (in milliseconds)")
define("auth", default='', help="comma separated list of emails", type=str)


class FlowerCommand(Command):

    def run_from_argv(self, prog_name, argv=None):
        app_settings = settings.APP_SETTINGS
        argv = filter(self.flower_option, argv)
        parse_command_line([prog_name] + argv)
        auth = map(str.strip, options.auth.split(',')) if options.auth else []
        app_settings['debug'] = options.debug
        settings.CELERY_INSPECT_TIMEOUT = options.inspect_timeout

        flower = Flower(celery_app=self.app, auth=auth, **app_settings)

        logging.info('Visit me at http://%s:%s' %
                (options.address or 'localhost', options.port))
        logging.info('Broker: %s', self.app.connection().as_uri())
        logging.debug('Settings: %s' % pformat(app_settings))

        try:
            flower.start(options.port, address=options.address,
                         inspect=options.inspect)
        except (KeyboardInterrupt, SystemExit):
            pass

    def handle_argv(self, prog_name, argv=None):
        return self.run_from_argv(prog_name, argv)

    @staticmethod
    def flower_option(arg):
        name, _, value = arg.lstrip('-').partition("=")
        name = name.replace('-', '_')
        return name in options
