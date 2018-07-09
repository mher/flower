from __future__ import absolute_import
from __future__ import with_statement

import json
import time
import logging
import threading
import collections
import traceback
from datetime import datetime, timedelta, date

from logging import config

import elasticsearch
import pytz
from elasticsearch import Elasticsearch, RequestsHttpConnection, TransportError, ElasticsearchException
from elasticsearch.helpers import bulk


from celery.events.state import State

from flower.events import Events
from . import api

from .options import options


try:
    from collections import Counter
except ImportError:
    from .utils.backports.collections import Counter


logger = logging.getLogger(__name__)
try:
    import queue
except:
    import Queue as queue


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'class': 'flower.logging_utils.CeleryOneLineExceptionFormatter',
            'format': '%(levelname)s %(asctime)s %(funcName)s %(module)s %(lineno)d %(message)s'
        },
    },
    'handlers': {
        'task_logger_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'task_logger.log',
            'formatter': 'verbose',
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'utc': True,
        },
        'stream': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'task_logger': {
            'handlers': ['task_logger_file', 'stream', ],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
config.dictConfig(LOGGING)

logger = logging.getLogger('task_logger')
ELASTICSEARCH_URL = options.elasticsearch_url
ES_INDEX_TIMEOUT = options.elasticsearch_index_timeout
ES_INDEX_BULK_SIZE = options.elasticsearch_index_bulk_size
ES_DAY_RETENTION = options.elasticsearch_day_retention


ES_CLIENT = Elasticsearch(
    [ELASTICSEARCH_URL],
    connection_class=RequestsHttpConnection
)

INDICES_CLIENT = ES_CLIENT.indices
# Index name states the day in which it was created -- not how long it is around for
index_name = 'task-{}'.format(datetime.utcnow().date().isoformat())

body = {
    'properties': {
        'hostname': {'type': 'keyword', },
        'worker': {'type': 'keyword', },
        'clock': {'type': 'integer', },
        'args': {'type': 'keyword', },
        'kwargs': {'type': 'keyword', },
        'timestamp_time': {'type': 'date', },
        'timestamp': {'type': 'float', },
        'root_id': {'type': 'keyword', },
        'root': {'type': 'keyword', },
        'parent_id': {'type': 'keyword', },
        'parent': {'type': 'keyword', },
        'name': {'type': 'keyword', },
        'result': {'type': 'keyword', },
        'state': {'type': 'keyword', },
        'eta': {'type': 'date', },
        'received': {'type': 'float', },
        'retries': {'type': 'integer', },
        'received_time': {
            "type": "date",
        },
        'expires': {'type': 'date', },
        'revoked': {'type': 'float', },
        'revoked_time': {
            "type": "date",
        },
        'retried': {'type': 'float', },
        'retried_time': {
            "type": "date",
        },
        'started': {'type': 'float', },
        'started_time': {
            "type": "date",
        },
        'failed': {'type': 'float', },
        'failed_time': {
            "type": "date",
        },
        'succeeded': {'type': 'float', },
        'succeeded_time': {
            "type": "date",
        },
        'runtime': {'type': 'float', },
        'info': {'type': 'text', },
        'traceback': {'type': 'text', },
        'exception': {'type': 'text', },
        '_fields': {'type': 'keyword', },
        'children': {'type': 'keyword', },
    }
}

es_queue = queue.Queue()


def es_consumer():
    es_buffer = []
    t = threading.currentThread()
    while getattr(t, "do_run", True):
        start_time = int(time.time())
        try:
            while len(es_buffer) < ES_INDEX_BULK_SIZE:
                es_buffer.append(es_queue.get(timeout=ES_INDEX_TIMEOUT))
                es_queue.task_done()
                got_task_time = int(time.time())
                if got_task_time - start_time >= ES_INDEX_TIMEOUT:
                    raise queue.Empty
        except queue.Empty:
            pass
        if es_buffer:
            for try_idx in range(5):
                # should consider implementing retry logic (outside of what the ES library uses)
                try:
                    bulk(actions=es_buffer, client=ES_CLIENT, stats_only=True)
                except (elasticsearch.ConnectionError, elasticsearch.ConnectionTimeout, ):
                    time.sleep(pow(2, try_idx))
                    logger.warning(traceback.format_exc())
                except elasticsearch.helpers.BulkIndexError:
                    time.sleep(pow(2, try_idx))
                    logger.warning(traceback.format_exc())
                    break
                except Exception:
                    es_buffer[:] = []
                    logger.warning(traceback.format_exc())
                    break
                else:
                    es_buffer[:] = []
                    break
            # Can enable the sleep in case it seems like we're writing into ES too frequently
            # time.sleep(0.5)


es_thread = threading.Thread(target=es_consumer)
es_thread.daemon = True


def send_to_elastic_search(state, event):
    # task name is sent only with -received event, and state
    # will keep track of this for us.
    if not event['type'].startswith('task-'):
        return
    task = state.tasks.get(event['uuid'])
    received_time = task.received
    succeeded_time = task.succeeded
    start_time = task.started

    # potentially use the sched module to change it via native python logic
    current_date = datetime.now(tz=pytz.utc).date()
    active_index_name = 'task-{}'.format(current_date.isoformat())
    global index_name
    if active_index_name != index_name:
        try:
            INDICES_CLIENT.create(index=active_index_name)
            INDICES_CLIENT.put_alias('task-*', 'task')
            INDICES_CLIENT.put_mapping(
                doc_type='task',
                body=body,
                index=active_index_name
            )
            index_name = active_index_name
        except TransportError:
            logger.warning("Issue creating or putting alias or mapping", traceback.format_exc())
        else:
            try:
                deleted = delete_old_elasticsearch_indices(current_date, ES_DAY_RETENTION)
                logger.info("Deleted the following older indices from day retention: "
                            "{day_retention}, "
                            "indices: {deleted}".format(day_retention=ES_DAY_RETENTION, deleted=deleted))
            except ElasticsearchException:
                logger.warning("Issue deleting older indices", exc_info=True)

    doc_body = {
        'hostname': task.hostname,
        'worker': task.hostname if task.worker else None,
        'exchange': task.exchange,
        'retries': task.retries,
        'routing_key': task.routing_key,
        'args': task.args,
        'kwargs': task.kwargs,
        'name': task.name,
        'clock': task.clock,
        'children': str(task.children) if task.children is not None else None,
        'expires': task.expires if task.expires else task.expires,
        'eta': task.eta,
        'state': task.state,
        'received': received_time,
        'received_time': datetime.utcfromtimestamp(received_time).replace(tzinfo=pytz.utc) if received_time else None,
        'retried': task.retried,
        'retried_time': datetime.utcfromtimestamp(task.retried).replace(tzinfo=pytz.utc) if task.retried else None,
        'started': start_time,
        'started_time': datetime.utcfromtimestamp(start_time).replace(tzinfo=pytz.utc) if start_time else None,
        'succeeded': succeeded_time,
        'succeeded_time': datetime.utcfromtimestamp(succeeded_time).replace(
            tzinfo=pytz.utc) if succeeded_time else None,
        'revoked': task.revoked,
        'revoked_time': datetime.utcfromtimestamp(task.revoked).replace(tzinfo=pytz.utc) if task.revoked else None,
        'failed': task.failed,
        'failed_time': datetime.utcfromtimestamp(task.failed).replace(tzinfo=pytz.utc) if task.failed else None,
        'info': json.dumps(task.info()),
        'result': task.result,
        'root_id': task.root_id,
        'root': str(task.root) if task.root else None,
        'runtime': task.runtime,
        'timestamp': task.timestamp,
        'timestamp_time': datetime.utcfromtimestamp(task.timestamp).replace(tzinfo=pytz.utc) if task.timestamp else None,
        'exception': task.exception,
        'traceback': task.traceback,
        'parent_id': task.parent_id,
        'parent': str(task.parent) if task.parent else None,
        '_fields': task._fields,
    }
    try:
        doc_body['_type'] = 'task'
        doc_body['_op_type'] = 'index'
        doc_body['_index'] = index_name
        doc_body['_id'] = task.uuid
        es_queue.put(doc_body)
    except Exception:
        logger.info('{name}[{uuid}] worker: {worker}, received: {received}, '
                    'started: {started}, succeeded: {succeeded}, info={info}'.format(name=task.name,
                                                                                     uuid=task.uuid,
                                                                                     worker=task.hostname,
                                                                                     info=task.info(),
                                                                                     received=received_time,
                                                                                     started=start_time,
                                                                                     succeeded=succeeded_time, ))


def delete_old_elasticsearch_indices(current_date, day_cut_off):
    if day_cut_off is None:
        return None
    date_cut_off = current_date - timedelta(days=day_cut_off)
    indices_return = ES_CLIENT.cat.indices(index="task", format="json", h="index")
    indices_return = [
        item["index"] for item in indices_return if
        date(
            year=int(item["index"].split("-")[1]),
            month=int(item["index"].split("-")[2]),
            day=int(item["index"].split("-")[3]))
        < date_cut_off
    ]
    if indices_return:
        return {"indices": indices_return, "response": ES_CLIENT.indices.delete(index=",".join(indices_return))}


class EventsState(State):
    # EventsState object is created and accessed only from ioloop thread

    def __init__(self, *args, **kwargs):
        super(EventsState, self).__init__(*args, **kwargs)
        self.counter = collections.defaultdict(Counter)

    def event(self, event):
        worker_name = event['hostname']
        event_type = event['type']

        if not event['type'].startswith('task-'):
            return

        # Send event to api subscribers (via websockets)
        classname = api.events.getClassName(event_type)
        cls = getattr(api.events, classname, None)
        if cls:
            cls.send_message(event)

        # Save the event
        super(EventsState, self).event(event)
        send_to_elastic_search(self, event)


class IndexerEvents(Events):
    events_enable_interval = 5000

    def __init__(self, capp, db=None, persistent=False,
                 enable_events=True, io_loop=None, **kwargs):

        super(IndexerEvents, self).__init__(capp=capp, db=db, persistent=persistent,
                                            enable_events=enable_events, io_loop=io_loop,
                                            **kwargs)
        try:
            INDICES_CLIENT.create(index=index_name)
        except TransportError as te:
            if te.error in ['index_already_exists_exception', 'resource_already_exists_exception']:
                pass
            else:
                logger.warning("Elastic search occurred, "
                               "may be bad: {}".format(traceback.format_exc()))
        try:
            INDICES_CLIENT.put_mapping(
                doc_type='task',
                body=body,
                index=index_name
            )
        except TransportError:
            logger.warning("Elastic search put mapping error (may be bad)", exc_info=True)
        try:
            if INDICES_CLIENT.exists(index=index_name):
                INDICES_CLIENT.put_alias('task-*', 'task')
        except TransportError:
            logger.warning("Elastic search exists/alias put error", exc_info=True)

        try:
            current_date = datetime.now(tz=pytz.utc).date()
            deleted = delete_old_elasticsearch_indices(current_date, ES_DAY_RETENTION)
            logger.info("Deleted the following older indices from day retention: "
                        "{day_retention}, "
                        "indices: {deleted}".format(day_retention=ES_DAY_RETENTION, deleted=deleted))
        except ElasticsearchException:
            logger.warning("Issue deleting older indices.", exc_info=True)

        self.state = EventsState(**kwargs)
