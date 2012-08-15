from __future__ import absolute_import

import logging

from pprint import pformat

from tornado import ioloop
from tornado.options import define, options, parse_command_line

from flower.app import create_application
from flower.settings import APP_SETTINGS

define("port", default=5555, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)
define("inspect", default=True, help="inspect workers", type=bool)


def main(argv=None):
    parse_command_line(argv)

    APP_SETTINGS['debug'] = options.debug

    app = create_application()
    if options.inspect:
        app.state.start()

    print('> Visit me at http://localhost:%s' % options.port)

    logging.debug('Settings: %s' % pformat(APP_SETTINGS))

    app.listen(options.port)
    try:
        ioloop.IOLoop.instance().start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
