import time
import shelve
import logging
import threading
import collections

from functools import partial

import celery

from tornado.ioloop import IOLoop
from tornado.ioloop import PeriodicCallback
from tornado.concurrent import run_on_executor

from celery.events import EventReceiver
from celery.events.state import State

from . import api

from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from prometheus_client import Counter as PrometheusCounter, Histogram

logger = logging.getLogger(__name__)


class PrometheusMetrics(object):
    events = PrometheusCounter('flower_events_total', "Number of events", ['worker', 'type', 'task'])
    runtime = Histogram('flower_task_runtime_seconds', "Task runtime", ['worker', 'task'])


class EventsState(State):
    # EventsState object is created and accessed only from ioloop thread

    def __init__(self, *args, **kwargs):
        super(EventsState, self).__init__(*args, **kwargs)
        self.counter = collections.defaultdict(Counter)
        self.metrics = PrometheusMetrics()

    def event(self, event):
        worker_name = event['hostname']
        event_type = event['type']

        self.counter[worker_name][event_type] += 1

        if event_type.startswith('task-'):
            task_id = event['uuid']
            task_name = event.get('name', '')
            if not task_name and task_id in self.tasks:
                task_name = self.tasks[task_id].name or ''
            self.metrics.events.labels(worker_name, event_type, task_name).inc()

            runtime = event.get('runtime', 0)
            if runtime:
                self.metrics.runtime.labels(worker_name, task_name).observe(runtime)

        # Send event to api subscribers (via websockets)
        classname = api.events.getClassName(event_type)
        cls = getattr(api.events, classname, None)
        if cls:
            cls.send_message(event)

        # Save the event
        super(EventsState, self).event(event)


class Events(threading.Thread):
    events_enable_interval = 5000

    def __init__(self, capp, db=None, persistent=False,
                 enable_events=True, io_loop=None, state_save_interval=0,
                 **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True

        self.io_loop = io_loop or IOLoop.instance()
        self.capp = capp

        self.db = db
        self.persistent = persistent
        self.enable_events = enable_events
        self.state = None
        self.state_save_timer = None

        if self.persistent:
            logger.debug("Loading state from '%s'...", self.db)
            state = shelve.open(self.db)
            if state:
                self.state = state['events']
            state.close()

            if state_save_interval:
                self.state_save_timer = PeriodicCallback(self.save_state,
                                                         state_save_interval)

        if not self.state:
            self.state = EventsState(**kwargs)

        self.timer = PeriodicCallback(self.on_enable_events,
                                      self.events_enable_interval)

    def start(self):
        threading.Thread.start(self)
        if self.enable_events:
            logger.debug("Starting enable events timer...")
            self.timer.start()

        if self.state_save_timer:
            logger.debug("Starting state save timer...")
            self.state_save_timer.start()

    def stop(self):
        if self.enable_events:
            logger.debug("Stopping enable events timer...")
            self.timer.stop()

        if self.state_save_timer:
            logger.debug("Stopping state save timer...")
            self.state_save_timer.stop()

        if self.persistent:
            self.save_state()

    def run(self):
        try_interval = 1
        while True:
            try:
                try_interval *= 2

                with self.capp.connection() as conn:
                    recv = EventReceiver(conn,
                                         handlers={"*": self.on_event},
                                         app=self.capp)
                    try_interval = 1
                    logger.debug("Capturing events...")
                    recv.capture(limit=None, timeout=None, wakeup=True)
            except (KeyboardInterrupt, SystemExit):
                try:
                    import _thread as thread
                except ImportError:
                    import thread
                thread.interrupt_main()
            except Exception as e:
                logger.error("Failed to capture events: '%s', "
                             "trying again in %s seconds.",
                             e, try_interval)
                logger.debug(e, exc_info=True)
                time.sleep(try_interval)

    def save_state(self):
        logger.debug("Saving state to '%s'...", self.db)
        state = shelve.open(self.db)
        state['events'] = self.state
        state.close()

    def on_enable_events(self):
        # Periodically enable events for workers
        # launched after flower
        self.io_loop.run_in_executor(None, self.capp.control.enable_events)

    def on_event(self, event):
        # Call EventsState.event in ioloop thread to avoid synchronization
        self.io_loop.add_callback(partial(self.state.event, event))
