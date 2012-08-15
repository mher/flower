import tornado.web

import celery

from flower.events import Events
from flower.state import State
from flower.urls import handlers
from flower.settings import APP_SETTINGS


class Application(tornado.web.Application):
    def __init__(self, celery_app, events, state, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)

        self.celery_app = celery_app
        self.events = events
        self.state = state


def create_application(options):
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

    return Application(celery_app, events, state, handlers, **APP_SETTINGS)
