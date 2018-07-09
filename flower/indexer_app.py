import celery
from tornado import ioloop

from flower.options import default_options


class IndexerApp(object):
    def __init__(self, options=None, capp=None, events=None, io_loop=None, **kwargs):
        super(IndexerApp, self).__init__()
        self.options = options or default_options
        self.io_loop = ioloop.IOLoop.instance()

        self.capp = capp or celery.Celery()
        from flower.elasticsearch_events import IndexerEvents, es_thread
        self.es_thread = es_thread
        self.events = events or IndexerEvents(
            self.capp, db=self.options.db,
            persistent=self.options.persistent,
            enable_events=self.options.enable_events,
            io_loop=self.io_loop,
            max_workers_in_memory=self.options.max_workers,
            max_tasks_in_memory=self.options.max_tasks)
        self.started = False

    def start(self):
        self.events.start()
        self.es_thread.start()
        self.started = True
        self.io_loop.start()

    def stop(self):
        if self.started:
            self.events.stop()
            self.es_thread.do_run = False
            self.es_thread.join(timeout=10)
            self.started = False

    @property
    def transport(self):
        return getattr(self.capp.connection().transport,
                       'driver_type', None)
