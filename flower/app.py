import tornado.web


class Application(tornado.web.Application):
    def __init__(self, celery_app, events, state, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)

        self.celery_app = celery_app
        self.events = events
        self.state = state
