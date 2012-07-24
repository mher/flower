from __future__ import absolute_import

import logging

from tornado import ioloop
from tornado.web import Application
from tornado.options import define, options, parse_command_line

from flower.state import state
from flower.events import EventCollector
from flower.urls import handlers
from flower.settings import APP_SETTINGS

define("port", default=8008, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)


def main(argv=None):
    parse_command_line(argv)

    APP_SETTINGS['debug'] = options.debug
    application = Application(handlers, **APP_SETTINGS)

    print('> visit me at http://localhost:%s' % options.port)

    logging.debug('Settings: %s' % APP_SETTINGS)

    application.listen(options.port)
    try:
        state.start()
        EventCollector().start()
        ioloop.IOLoop.instance().start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
