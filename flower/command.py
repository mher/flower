from __future__ import absolute_import
from __future__ import print_function

import atexit
import logging
import signal
import sys
import os

from pprint import pformat

from tornado.options import define, options
from tornado.log import enable_pretty_logging
from tornado.options import parse_command_line, parse_config_file
from tornado.auth import GoogleOAuth2Mixin

from celery.bin.base import Command

from . import settings
from . import __version__
from .app import Flower


define("port", default=5555, help="run on the given port", type=int)
define("address", default='', help="run on the given address", type=str)
define("debug", default=False, help="run in debug mode", type=bool)
define("inspect", default=True, help="inspect workers", type=bool)
define("inspect_timeout", default=1000, type=float,
       help="inspect timeout (in milliseconds)")
define("auth", default='', type=str,
       help="regexp of emails to grant access")
define("basic_auth", type=str, default=None, multiple=True,
       help="enable http basic authentication")
define("oauth2_key", type=str, default=None, help="Google oauth2 key (requires --auth)")
define("oauth2_secret", type=str, default=None, help="Google oauth2 secret (requires --auth)")
define("oauth2_redirect_uri", type=str, default=None, help="Google oauth2 redirect uri (requires --auth)")
define("url_prefix", type=str, help="base url prefix")
define("max_tasks", type=int, default=10000,
       help="maximum number of tasks to keep in memory (default 10000)")
define("db", type=str, default='flower', help="flower database file")
define("persistent", type=bool, default=False, help="enable persistent mode")
define("broker_api", type=str, default=None,
       help="inspect broker e.g. http://guest:guest@localhost:15672/api/")
define("certfile", type=str, default=None, help="path to SSL certificate file")
define("keyfile", type=str, default=None, help="path to SSL key file")
define("xheaders", type=bool, default=False,
       help="enable support for the 'X-Real-Ip' and 'X-Scheme' headers.")
define("auto_refresh", default=True, help="refresh dashboards", type=bool)
define("cookie_secret", type=str, default=None, help="secure cookie secret")
define("conf", default=settings.CONFIG_FILE, help="configuration file")


logger = logging.getLogger(__name__)


class FlowerCommand(Command):

    def run_from_argv(self, prog_name, argv=None, **_kwargs):
        app_settings = settings.APP_SETTINGS
        argv = list(filter(self.flower_option, argv))
        # parse the command line to get --conf option
        parse_command_line([prog_name] + argv)
        try:
            parse_config_file(options.conf, final=False)
            parse_command_line([prog_name] + argv)
        except IOError:
            if options.conf != settings.CONFIG_FILE:
                raise

        app_settings['debug'] = options.debug
        if options.cookie_secret:
            app_settings['cookie_secret'] = options.cookie_secret

        if options.url_prefix:
            prefix = options.url_prefix.strip('/')
            app_settings['static_url_prefix'] = '/{0}/static/'.format(prefix)
            app_settings['login_url'] = '/{0}/login'.format(prefix)
            settings.URL_PREFIX = prefix
        settings.CELERY_INSPECT_TIMEOUT = options.inspect_timeout
        settings.AUTO_REFRESH = options.auto_refresh

        if options.debug and options.logging == 'info':
            options.logging = 'debug'
            enable_pretty_logging()

        if options.auth:
            app_settings[GoogleOAuth2Mixin._OAUTH_SETTINGS_KEY] = {
              'key': options.oauth2_key or os.environ.get('GOOGLE_OAUTH2_KEY'),
              'secret': options.oauth2_secret or os.environ.get('GOOGLE_OAUTH2_SECRET'),
              'redirect_uri': options.oauth2_redirect_uri or os.environ.get('GOOGLE_OAUTH2_REDIRECT_URI'),
            }

        # Monkey-patch to support Celery 2.5.5
        self.app.connection = self.app.broker_connection

        self.app.loader.import_default_modules()
        flower = Flower(celery_app=self.app, options=options,
                        **app_settings)
        atexit.register(flower.stop)

        # graceful shutdown on SIGTERM
        def signal_handler(signal, frame):
            logger.info('SIGTERM detected, shutting down')
            sys.exit(0)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info('Visit me at http%s://%s:%s',
                    's' if flower.ssl else '',
                    options.address or 'localhost',
                    options.port)
        logger.info('Broker: %s', self.app.connection().as_uri())
        logger.debug('Registered tasks: \n%s',
                     pformat(sorted(self.app.tasks.keys())))
        logger.debug('Settings: %s', pformat(app_settings))

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
    def flower_option(arg):
        name, _, value = arg.lstrip('-').partition("=")
        name = name.replace('-', '_')
        return hasattr(options, name)
