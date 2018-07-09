from __future__ import absolute_import

import logging

from tornado import web

try:
    from elasticsearch import Elasticsearch, TransportError
except ImportError:
    Elasticsearch = None
    TransportError = None

from tornado.web import HTTPError

from ..options import options

from ..views import BaseHandler

logger = logging.getLogger(__name__)


class ElasticSearchHistoryHandler(BaseHandler):
    def __init__(self):
        elasticsearch_url = options.elasticsearch_url
        if elasticsearch_url:
            self.es = Elasticsearch([elasticsearch_url, ])
        else:
            self.es = None

    @web.authenticated
    def post(self, index_name=None):
        index_name = index_name or 'task'
        try:
            self.es.indices.refresh(index_name)
        except TransportError as e:
            raise HTTPError(400, 'Invalid option: {}'.format(e))
        else:
            response = u'Successful refresh on index: {}'.format(index_name)
            self.write(response)


class AlternativeBackendError(Exception):
    pass


def list_tasks_elastic_search(argument_getter):
    from elasticsearch import Elasticsearch, TransportError

    elasticsearch_url = options.elasticsearch_url

    es = Elasticsearch([elasticsearch_url, ])
    limit = argument_getter.get_argument('limit', None)
    worker = argument_getter.get_argument('workername', None)
    task_name = argument_getter.get_argument('taskname', None)
    state = argument_getter.get_argument('state', None)
    received_start = argument_getter.get_argument('received_start', None)
    received_end = argument_getter.get_argument('received_end', None)
    started_start = argument_getter.get_argument('started_start', None)
    started_end = argument_getter.get_argument('started_end', None)
    root_id = argument_getter.get_argument('root_id', None)
    parent_id = argument_getter.get_argument('parent_id', None)
    runtime_lt = argument_getter.get_argument('runtime_lt', None)
    runtime_gt = argument_getter.get_argument('runtime_gt', None)
    result = []
    limit = limit and int(limit)
    worker = worker if worker != 'All' else None
    task_name = task_name if task_name != 'All' else None
    state = state if state != 'All' else None
    from elasticsearch_dsl import Search
    from elasticsearch_dsl.query import Term, Range
    s = Search(using=es, index='task')
    try:
        if worker:
            s = s.filter(Term(hostname=worker))
        if type:
            s = s.filter(Term(name=task_name))
        if state:
            s = s.filter(Term(state=state))
        if root_id:
            s = s.filter(Term(root_id=root_id))
        if parent_id:
            s = s.filter(Term(parent_id=parent_id))
        if received_start:
            s = s.filter(Range(received_time=dict(gt=received_start)))
        if received_end:
            s = s.filter(Range(received_time=dict(lt=received_end)))
        if started_start:
            s = s.filter(Range(started_time=dict(gt=started_start)))
        if started_end:
            s = s.filter(Range(started_time=dict(lt=started_end)))
        if runtime_lt is not None:
            s = s.query(Range(runtime=dict(lt=float(runtime_lt))))
        if runtime_gt is not None:
            s = s.query(Range(runtime=dict(gt=float(runtime_gt))))
        if limit is not None:
            s = s.extra(size=limit)
        hit_dicts = s.execute().hits.hits
        for hit_dict in hit_dicts:
            result.append((hit_dict['_id'], hit_dict['_source']))
    except TransportError as e:
        logger.warning("Issue querying task API via Elasticsearch", exc_info=True)
        raise AlternativeBackendError()
    else:
        return result
