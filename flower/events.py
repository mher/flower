import time
import shelve
import logging
import threading
import collections

from functools import partial

import prometheus_client
from tornado.ioloop import IOLoop
from tornado.ioloop import PeriodicCallback

from celery.events import EventReceiver
from celery.events.state import State

from . import api
from .options import options
# from options import options

from collections import Counter

from prometheus_client import Counter as PrometheusCounter, Histogram, Gauge

logger = logging.getLogger(__name__)


class PrometheusMetrics(object):
    events = PrometheusCounter('flower_events_total', "Number of events", ['worker', 'type', 'task'])
    runtime = Histogram('flower_task_runtime_seconds', "Task runtime", ['worker', 'task'])
    prefetch_time = Gauge(
        'flower_task_prefetch_time_seconds',
        "The time the task spent waiting at the celery worker to be executed.",
        ['worker', 'task']
    )
    number_of_prefetched_tasks = Gauge(
        'flower_worker_prefetched_tasks',
        'Number of tasks of given type prefetched at a worker',
        ['worker', 'task']
    )
    worker_online = Gauge('flower_worker_online', "Worker online status", ['worker'])
    worker_number_of_currently_executing_tasks = Gauge(
        'flower_worker_number_of_currently_executing_tasks',
        "Number of tasks currently executing at a worker",
        ['worker']
    )


class EventsState(State):
    # EventsState object is created and accessed only from ioloop thread

    def __init__(self, *args, **kwargs):
        super(EventsState, self).__init__(*args, **kwargs)
        self.counter = collections.defaultdict(Counter)
        self.metrics = PrometheusMetrics()

    def event(self, event):
        # Save the event
        super(EventsState, self).event(event)

        worker_name = event['hostname']
        event_type = event['type']

        self.counter[worker_name][event_type] += 1

        if event_type.startswith('task-'):
            task_id = event['uuid']
            task = self.tasks.get(task_id)
            task_name = event.get('name', '')
            if not task_name and task_id in self.tasks:
                task_name = task.name or ''
            self.metrics.events.labels(worker_name, event_type, task_name).inc()

            runtime = event.get('runtime', 0)
            if runtime:
                self.metrics.runtime.labels(worker_name, task_name).observe(runtime)

            task_started = task.started
            task_received = task.received

            if event_type == 'task-received' and not task.eta and task_received:
                self.metrics.number_of_prefetched_tasks.labels(worker_name, task_name).inc()

            if event_type == 'task-started' and not task.eta and task_started and task_received:
                self.metrics.prefetch_time.labels(worker_name, task_name).set(task_started - task_received)
                self.metrics.number_of_prefetched_tasks.labels(worker_name, task_name).dec()

            if event_type in ['task-succeeded', 'task-failed'] and not task.eta and task_started and task_received:
                self.metrics.prefetch_time.labels(worker_name, task_name).set(0)

        if event_type == 'worker-online':
            self.metrics.worker_online.labels(worker_name).set(1)

        if event_type == 'worker-heartbeat':
            self.metrics.worker_online.labels(worker_name).set(1)

            num_executing_tasks = event.get('active')
            if num_executing_tasks is not None:
                self.metrics.worker_number_of_currently_executing_tasks.labels(worker_name).set(num_executing_tasks)

        if event_type == 'worker-offline':
            self.metrics.worker_online.labels(worker_name).set(0)

        # Send event to api subscribers (via websockets)
        classname = api.events.getClassName(event_type)
        cls = getattr(api.events, classname, None)
        if cls:
            cls.send_message(event)

        # purging logic copy pasted for testing
        workers = {}
        for name, values in self.counter.items():
            if name not in self.workers:
                continue
            worker = self.workers[name]
            info = dict(values)
            info.update(self._as_dict(worker))
            info.update(status=worker.alive)
            workers[name] = info

        if options.purge_offline_workers is not None:
            timestamp = int(time.time())
            offline_workers = []
            for name, info in workers.items():
                if info.get('status', True):
                    continue

                heartbeats = info.get('heartbeats', [])
                last_heartbeat = int(max(heartbeats)) if heartbeats else None
                if not last_heartbeat or timestamp - last_heartbeat > options.purge_offline_workers:
                    logger.debug('Offline worker found: %s', name)
                    offline_workers.append(name)

            for name in offline_workers:
                self.metrics.worker_online.remove(name)
                logger.debug('Removing worker from worker online metric: %s', name)
                workers.pop(name)

    @classmethod
    def _as_dict(cls, worker):
        if hasattr(worker, '_fields'):
            return dict((k, worker.__getattribute__(k)) for k in worker._fields)
        else:
            return cls._info(worker)

    @classmethod
    def _info(cls, worker):
        _fields = ('hostname', 'pid', 'freq', 'heartbeats', 'clock',
                   'active', 'processed', 'loadavg', 'sw_ident',
                   'sw_ver', 'sw_sys')

        def _keys():
            for key in _fields:
                value = getattr(worker, key, None)
                if value is not None:
                    yield key, value

        return dict(_keys())


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
        state = shelve.open(self.db, flag='n')
        state['events'] = self.state
        state.close()

    def on_enable_events(self):
        # Periodically enable events for workers
        # launched after flower
        self.io_loop.run_in_executor(None, self.capp.control.enable_events)

    def on_event(self, event):
        # Call EventsState.event in ioloop thread to avoid synchronization
        self.io_loop.add_callback(partial(self.state.event, event))
