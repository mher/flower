import collections
import logging
import queue
import shelve
import threading
import time
from collections import Counter
from functools import partial

from celery.events import EventReceiver
from celery.events.state import State
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge, Histogram
from tornado.ioloop import PeriodicCallback
from tornado.options import options

logger = logging.getLogger(__name__)

PROMETHEUS_METRICS = None

MAX_RETRY_INTERVAL = 60


def get_prometheus_metrics():
    global PROMETHEUS_METRICS  # pylint: disable=global-statement
    if PROMETHEUS_METRICS is None:
        PROMETHEUS_METRICS = PrometheusMetrics()

    return PROMETHEUS_METRICS


class PrometheusMetrics:
    def __init__(self):
        self.events = PrometheusCounter('flower_events_total', "Number of events", ['worker', 'type', 'task'])

        self.runtime = Histogram(
            'flower_task_runtime_seconds',
            "Task runtime",
            ['worker', 'task'],
            buckets=options.task_runtime_metric_buckets
        )
        self.prefetch_time = Gauge(
            'flower_task_prefetch_time_seconds',
            "The time the task spent waiting at the celery worker to be executed.",
            ['worker', 'task']
        )
        self.number_of_prefetched_tasks = Gauge(
            'flower_worker_prefetched_tasks',
            'Number of tasks of given type prefetched at a worker',
            ['worker', 'task']
        )
        self.worker_online = Gauge('flower_worker_online', "Worker online status", ['worker'])
        self.worker_number_of_currently_executing_tasks = Gauge(
            'flower_worker_number_of_currently_executing_tasks',
            "Number of tasks currently executing at a worker",
            ['worker']
        )


class EventsState(State):
    # EventsState object is created and accessed only from ioloop thread

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = collections.defaultdict(Counter)
        self.metrics = get_prometheus_metrics()

    def event(self, event):
        # Save the event
        super().event(event)

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


class Events(threading.Thread):
    events_enable_interval = 5000
    _BACKPRESSURE_MAXSIZE = 10000
    _DRAIN_INTERVAL_MS = 100
    _DRAIN_BATCH_SIZE = 500

    # pylint: disable=too-many-arguments
    def __init__(self, capp, io_loop, db=None, persistent=False,
                 enable_events=True, state_save_interval=0,
                 **kwargs):
        threading.Thread.__init__(self)
        self.daemon = True

        self.io_loop = io_loop
        self.capp = capp

        self.db = db
        self.persistent = persistent
        self.enable_events = enable_events
        self.state = None
        self.state_save_timer = None
        self._drain_timer = None
        self._event_queue = queue.Queue(maxsize=self._BACKPRESSURE_MAXSIZE)
        self._drop_count = 0
        self._last_drop_log_time = 0.0

        if self.persistent:
            logger.debug("Loading state from '%s'...", self.db)
            try:
                with shelve.open(self.db) as state:
                    if state:
                        self.state = state['events']
            except KeyError:
                logger.debug("No existing state found in '%s'", self.db)
            except Exception:
                logger.error("Failed to load state from '%s'", self.db, exc_info=True)

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

        self._drain_timer = PeriodicCallback(self._drain_events,
                                             self._DRAIN_INTERVAL_MS)
        self._drain_timer.start()

    def stop(self):
        try:
            if self.enable_events:
                logger.debug("Stopping enable events timer...")
                try:
                    self.timer.stop()
                except Exception:
                    logger.debug("Error stopping enable events timer", exc_info=True)

            if self.state_save_timer:
                logger.debug("Stopping state save timer...")
                try:
                    self.state_save_timer.stop()
                except Exception:
                    logger.debug("Error stopping state save timer", exc_info=True)

            if self._drain_timer:
                try:
                    self._drain_timer.stop()
                except Exception:
                    logger.debug("Error stopping drain timer", exc_info=True)
        finally:
            if self.persistent:
                self.save_state()

    def run(self):
        try_interval = 1
        while True:
            try:
                try_interval *= 2
                if try_interval > MAX_RETRY_INTERVAL:
                    try_interval = MAX_RETRY_INTERVAL

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
        try:
            with shelve.open(self.db, flag='n') as state:
                state['events'] = self.state
        except Exception:
            logger.error("Failed to save state to '%s'", self.db, exc_info=True)

    def on_enable_events(self):
        # Periodically enable events for workers
        # launched after flower
        self.io_loop.run_in_executor(None, self.capp.control.enable_events)

    def on_event(self, event):
        # Enqueue event with backpressure — drop if queue is full.
        # Rate-limit drop warnings to avoid flooding logs under sustained load.
        try:
            self._event_queue.put_nowait(event)
        except queue.Full:
            self._drop_count += 1
            now = time.monotonic()
            if now - self._last_drop_log_time >= 5.0:
                window_start = self._last_drop_log_time or now
                duration = now - window_start
                logger.warning(
                    "Event queue full (%d), dropped %d event(s) in last %.0fs",
                    self._BACKPRESSURE_MAXSIZE, self._drop_count, duration)
                self._drop_count = 0
                self._last_drop_log_time = now

    def _drain_events(self):
        """Process up to _DRAIN_BATCH_SIZE events from the backpressure queue."""
        for _ in range(self._DRAIN_BATCH_SIZE):
            try:
                event = self._event_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self.state.event(event)
            except Exception:
                logger.error("Error processing event", exc_info=True)
