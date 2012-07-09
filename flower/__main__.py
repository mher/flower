from __future__ import absolute_import

from tornado import ioloop
from tornado.web import Application
from tornado.options import define, options, parse_command_line

from .state import state
from .events import EventCollector
from .urls import handlers
from .settings import APP_SETTINGS

define("port", default=8008, help="run on the given port", type=int)


def main(argv=None):
    parse_command_line(argv)

    application = Application(handlers, **APP_SETTINGS)

    print('> visit me at http://localhost:%s' % options.port)

    application.listen(options.port)
    try:
        state.start()
        EventCollector().start()
        ioloop.IOLoop.instance().start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
