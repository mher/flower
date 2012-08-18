from __future__ import absolute_import

import logging

from pprint import pformat

from tornado.options import define, options, parse_command_line

from celery.bin.base import Command

from .app import Flower
from .settings import APP_SETTINGS

define("port", default=5555, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)
define("inspect", default=True, help="inspect workers", type=bool)


class FlowerCommand(Command):

    def handle_argv(self, prog_name, argv=None):
        argv = filter(self.flower_option, argv)
        parse_command_line([prog_name] + argv)
        APP_SETTINGS['debug'] = options.debug

        flower = Flower(celery_app=self.app, **APP_SETTINGS)

        logging.info('Visit me at http://localhost:%s' % options.port)
        logging.info('Broker: %s', self.app.connection().as_uri())
        logging.debug('Settings: %s' % pformat(APP_SETTINGS))

        try:
            flower.start(options.port, inspect=options.inspect)
        except (KeyboardInterrupt, SystemExit):
            pass

    @staticmethod
    def flower_option(arg):
        name, _, value = arg.lstrip('-').partition("=")
        name = name.replace('-', '_')
        return name in options
