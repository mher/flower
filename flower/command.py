import os
import sys
import atexit
import signal
import logging

from pprint import pformat

from logging import NullHandler

import click
from tornado.options import options
from tornado.options import parse_command_line, parse_config_file
from tornado.log import enable_pretty_logging
from celery.bin.base import CeleryCommand

from .app import Flower
from .urls import settings
from .utils import abs_path, prepend_url, strtobool
from .options import DEFAULT_CONFIG_FILE, default_options
from .views.auth import validate_auth_option

logger = logging.getLogger(__name__)
ENV_VAR_PREFIX = 'FLOWER_'


def sigterm_handler(signum, _):
    logger.info('%s detected, shutting down', signum)
    sys.exit(0)


@click.command(cls=CeleryCommand,
               context_settings={
                   'ignore_unknown_options': True
               })
@click.argument("tornado_argv", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def flower(ctx, tornado_argv):
    """Web based tool for monitoring and administrating Celery clusters."""
    warn_about_celery_args_used_in_flower_command(ctx, tornado_argv)
    apply_env_options()
    apply_options(sys.argv[0], tornado_argv)

    extract_settings()
    setup_logging()

    app = ctx.obj.app
    flower_app = Flower(capp=app, options=options, **settings)

    atexit.register(flower_app.stop)
    signal.signal(signal.SIGTERM, sigterm_handler)

    if not ctx.obj.quiet:
        print_banner(app, 'ssl_options' in settings)

    try:
        flower_app.start()
    except (KeyboardInterrupt, SystemExit):
        pass


def apply_env_options():
    "apply options passed through environment variables"
    env_options = filter(is_flower_envvar, os.environ)
    for env_var_name in env_options:
        name = env_var_name.replace(ENV_VAR_PREFIX, '', 1).lower()
        value = os.environ[env_var_name]
        try:
            option = options._options[name]  # pylint: disable=protected-access
        except KeyError:
            option = options._options[name.replace('_', '-')]  # pylint: disable=protected-access
        if option.multiple:
            value = [option.type(i) for i in value.split(',')]
        else:
            if option.type is bool:
                value = bool(strtobool(value))
            else:
                value = option.type(value)
        setattr(options, name, value)


def apply_options(prog_name, argv):
    "apply options passed through the configuration file"
    argv = list(filter(is_flower_option, argv))
    # parse the command line to get --conf option
    parse_command_line([prog_name] + argv)
    try:
        parse_config_file(os.path.abspath(options.conf), final=False)
        parse_command_line([prog_name] + argv)
    except IOError:
        if os.path.basename(options.conf) != DEFAULT_CONFIG_FILE:
            raise


def warn_about_celery_args_used_in_flower_command(ctx, flower_args):
    celery_options = [option for param in ctx.parent.command.params for option in param.opts]

    incorrectly_used_args = []
    for arg in flower_args:
        arg_name, _, _ = arg.partition("=")
        if arg_name in celery_options:
            incorrectly_used_args.append(arg_name)

    if incorrectly_used_args:
        logger.warning(
            'You have incorrectly specified the following celery arguments after flower command:'
            ' %s. '
            'Please specify them after celery command instead following this template: '
            'celery [celery args] flower [flower args].', incorrectly_used_args
        )


def setup_logging():
    if options.debug and options.logging == 'info':
        options.logging = 'debug'
        enable_pretty_logging()
    else:
        logging.getLogger("tornado.access").addHandler(NullHandler())
        logging.getLogger("tornado.access").propagate = False


def extract_settings():
    settings['debug'] = options.debug

    if options.cookie_secret:
        settings['cookie_secret'] = options.cookie_secret

    if options.url_prefix:
        for name in ['login_url', 'static_url_prefix']:
            settings[name] = prepend_url(settings[name], options.url_prefix)

    if options.auth:
        settings['oauth'] = {
            'key': options.oauth2_key or os.environ.get('FLOWER_OAUTH2_KEY'),
            'secret': options.oauth2_secret or os.environ.get('FLOWER_OAUTH2_SECRET'),
            'redirect_uri': options.oauth2_redirect_uri or os.environ.get('FLOWER_OAUTH2_REDIRECT_URI'),
        }

    if options.certfile and options.keyfile:
        settings['ssl_options'] = dict(certfile=abs_path(options.certfile),
                                       keyfile=abs_path(options.keyfile))
        if options.ca_certs:
            settings['ssl_options']['ca_certs'] = abs_path(options.ca_certs)

    if options.auth and not validate_auth_option(options.auth):
        logger.error("Invalid '--auth' option: %s", options.auth)
        sys.exit(1)


def is_flower_option(arg):
    name, _, _ = arg.lstrip('-').partition("=")
    name = name.replace('-', '_')
    return hasattr(options, name)


def is_flower_envvar(name):
    return name.startswith(ENV_VAR_PREFIX) and \
        name[len(ENV_VAR_PREFIX):].lower() in default_options


def print_banner(app, ssl):
    if not options.unix_socket:
        if options.url_prefix:
            prefix_str = f'/{options.url_prefix}/'
        else:
            prefix_str = ''

        logger.info(
            "Visit me at http%s://%s:%s%s", 's' if ssl else '',
            options.address or '0.0.0.0', options.port,
            prefix_str
        )
    else:
        logger.info("Visit me via unix socket file: %s", options.unix_socket)

    logger.info('Broker: %s', app.connection().as_uri())
    logger.info(
        'Registered tasks: \n%s',
        pformat(sorted(app.tasks.keys()))
    )
    logger.debug('Settings: %s', pformat(settings))
