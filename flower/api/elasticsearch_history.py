from __future__ import absolute_import

import logging
import typing

from tornado import web
from tornado.web import HTTPError

try:
    from elasticsearch import Elasticsearch, TransportError
    from elasticsearch_dsl import Search
    from elasticsearch_dsl.query import Range, Term
except ImportError:
    Elasticsearch = None
    TransportError = None
    Search = None
    Term = None
    Range = None



from ..options import options
# need to be able to use satisfies_search_terms first
# from .search import parse_search_terms, satisfies_search_terms
from ..views import BaseHandler

logger = logging.getLogger(__name__)


sort_keys = {'name': str, 'state': str, 'received': float, 'started': float}
sort_key_alias = {'name': 'name', 'state': 'state', 'received': 'received_time', 'started': 'started_time'}


class ElasticSearchHistoryHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        elasticsearch_url = options.elasticsearch_url
        if elasticsearch_url:
            self.es = Elasticsearch([elasticsearch_url, ])
        else:
            self.es = None

        super().__init__(*args, **kwargs)

    @web.authenticated
    def post(self, index_name: typing.Optional[str]=None):
        index_name = index_name or 'task'
        try:
            self.es.indices.refresh(index_name)
        except TransportError as e:
            raise HTTPError(400, f'Invalid option: {e}') from e
        response = f'Successful refresh on index: {index_name}'
        self.write(response)


class AlternativeBackendError(Exception):
    pass


def list_tasks_elastic_search(argument_getter):
    elasticsearch_url = options.elasticsearch_url

    es = Elasticsearch([elasticsearch_url, ])


    s = Search(using=es, index='task')
    result = []
    try:
        s = build_search_with_fields(argument_getter, s)
        hit_dicts = s.execute().hits.hits
        for hit_dict in hit_dicts:
            result.append((hit_dict['_id'], hit_dict['_source']))
    except TransportError as exc:
        logger.warning("Issue querying task API via Elasticsearch", exc_info=True)
        raise AlternativeBackendError() from exc
    return result

# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
def build_search_with_fields(argument_getter, s):
    limit = argument_getter.get_argument('limit', None)
    worker = argument_getter.get_argument('workername', None)
    task_name = argument_getter.get_argument('taskname', None)
    state = argument_getter.get_argument('state', None)
    received_start = argument_getter.get_argument('received_start', None)
    received_end = argument_getter.get_argument('received_end', None)
    sort_by = argument_getter.get_argument('sort_by', None)
    # need to be able to use satisfies_search_terms first
    # search = argument_getter.get_argument('search', None)
    started_start = argument_getter.get_argument('started_start', None)
    started_end = argument_getter.get_argument('started_end', None)
    root_id = argument_getter.get_argument('root_id', None)
    parent_id = argument_getter.get_argument('parent_id', None)
    runtime_lt = argument_getter.get_argument('runtime_lt', None)
    runtime_gt = argument_getter.get_argument('runtime_gt', None)

    limit = limit and int(limit)
    worker = worker if worker != 'All' else None
    task_name = task_name if task_name != 'All' else None
    state = state if state != 'All' else None

    # need to be able to use satisfies_search_terms first
    # search_terms = parse_search_terms(search or {})
    if worker:
        s = s.filter(Term(hostname=worker))
    if task_name:
        s = s.filter(Term(name=task_name))
    if state:
        s = s.filter(Term(state=state))
    if root_id:
        s = s.filter(Term(root_id=root_id))
    if parent_id:
        s = s.filter(Term(parent_id=parent_id))
    time_based_filtering_tuples = [("received_time", "gt", received_start), ("received_time", "lt", received_end), ("started_time", "gt", started_start), ("started_time", "lt", started_end)]
    for key, comp_key, value in time_based_filtering_tuples:
        if value:
            s = s.filter(Range(**{key: {comp_key: value}}))

    if runtime_lt is not None:
        s = s.query(Range(runtime=dict(lt=float(runtime_lt))))
    if runtime_gt is not None:
        s = s.query(Range(runtime=dict(gt=float(runtime_gt))))
    # satisfies_search_terms would be ideal to use -- maybe take the `Hit` logic in task view
    # and apply that here so it could do the attr lookup as is.
    # if not satisfies_search_terms(task, search_terms):
    #     continue
    if limit is not None:
        s = s.extra(size=limit)
    if sort_by is not None:
        reverse = False
        if sort_by.startswith('-'):
            sort_by = sort_by.lstrip('-')
            reverse = True

        if sort_by in sort_keys:
            s = s.sort({sort_key_alias.get(sort_by, sort_by): {"order": "desc" if reverse else "asc"}})
    return s
