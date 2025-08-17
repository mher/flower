import collections
import logging
import shelve
import threading
import time
from collections import defaultdict, Counter
from functools import partial

from celery.events import EventReceiver
from celery.events.state import State
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge, Histogram
from tornado.ioloop import PeriodicCallback
from tornado.options import options


try:
    from elasticsearch import Elasticsearch
    from elasticsearch_dsl import Search, MultiSearch
    from elasticsearch_dsl.query import Term
except ImportError:
    Search = None
    Elasticsearch = None
    MultiSearch = None
    Term = None

logger = logging.getLogger(__name__)

PROMETHEUS_METRICS = None


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

        if not self.counter[worker_name] and options.elasticsearch_dashboard is True:
            event_type = self.elasticsearch_dashboard_data(worker_name, event_type)
        else:
            self.counter[worker_name][event_type] += 1

        if event_type.startswith('task-'):
            task_id = event.get('uuid')
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

    # pylint: disable=too-many-locals
    def elasticsearch_dashboard_data(self, worker_name, event_type):
        elasticsearch_url = options.elasticsearch_url
        es = Elasticsearch([elasticsearch_url, ])

        ms = MultiSearch(using=es, index="task")
        s = Search(using=es, index='task')
        ms = ms.add(s.filter(Term(state='RECEIVED') & Term(hostname=worker_name)).extra(size=0))  # pylint: disable=no-member
        ms = ms.add(s.filter(Term(state='STARTED') & Term(hostname=worker_name)).extra(size=0)) # pylint: disable=no-member
        ms = ms.add(s.filter(Term(state='SUCCESS') & Term(hostname=worker_name)).extra(size=0)) # pylint: disable=no-member
        ms = ms.add(s.filter(Term(state='FAILED') & Term(hostname=worker_name)).extra(size=0))  # pylint: disable=no-member
        ms = ms.add(s.filter(Term(state='RETRIED') & Term(hostname=worker_name)).extra(size=0))  # pylint: disable=no-member
        responses = ms.execute()
        task_event_keys = ["task-received", "task-started", "task-succeeded", "task-failed", "task-retried"]
        tasks_info = defaultdict(int)
        for event_type_item, resp in zip(task_event_keys, responses):
            tasks_info[event_type_item] += resp.hits.total
        processed = tasks_info["task-received"]
        started = tasks_info["task-started"]
        succeeded = tasks_info["task-succeeded"]
        failed = tasks_info["task-failed"]
        retried = tasks_info["task-retried"]
        self.counter[worker_name]['task-received'] = processed + started + succeeded + failed + retried
        self.counter[worker_name]['task-started'] = started
        self.counter[worker_name]['task-succeeded'] = succeeded
        self.counter[worker_name]['task-retried'] = retried
        self.counter[worker_name]['task-failed'] = failed
        if not event_type.startswith('task-'):
            self.counter[worker_name][event_type] += 1
        return event_type

        # from .elasticsearch_history import send_to_elastic_search
        # try:
        #     send_to_elastic_search(self, event)
        # except Exception as e:
        #     print(e)


class Events(threading.Thread):
    events_enable_interval = 5000

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
