from __future__ import absolute_import

import logging

from pprint import pformat

from tornado import ioloop
from tornado.options import define, options, parse_command_line

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers
from flower.app import Application
from flower.settings import APP_SETTINGS

define("port", default=5555, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)
define("inspect", default=True, help="inspect workers", type=bool)


def main(argv=None):
    parse_command_line(argv)

    APP_SETTINGS['debug'] = options.debug

    celery_app = celery.Celery()
    try:
        celery_app.config_from_object('celeryconfig')
    except ImportError:
        pass

    events = Events(celery_app)
    events.start()
    state = State(celery_app)
    if options.inspect:
        state.start()

    app = Application(celery_app, events, state, handlers, **APP_SETTINGS)

    print('> Visit me at http://localhost:%s' % options.port)

    logging.debug('Settings: %s' % pformat(APP_SETTINGS))

    app.listen(options.port)
    try:
        ioloop.IOLoop.instance().start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
