import copy
import datetime
import logging
import re
import time
import typing
from functools import total_ordering

from celery.events.state import Task
from kombu.utils.functional import LRUCache
from tornado import web

from ..events import Events
from ..options import options as runtime_options
from ..utils.search import parse_search_terms
from ..utils.tasks import as_dict, get_task_by_id, iter_tasks
from ..views import BaseHandler

try:
    from elasticsearch.client import Elasticsearch
    from elasticsearch.exceptions import TransportError
    from elasticsearch_dsl import Search
    from elasticsearch_dsl.query import Match, Range, Term, Terms, Wildcard
    from elasticsearch_dsl.search import Hit

except ImportError:
    Elasticsearch = None
    Match = None
    TransportError = None
    Search = None
    Wildcard = None
    Terms = None
    Term = None
    Range = None
    Hit = None

logger = logging.getLogger(__name__)


class TaskView(BaseHandler):
    def __init__(self, *args, **kwargs):
        self.use_es = runtime_options.elasticsearch
        self.elasticsearch_url = runtime_options.elasticsearch_url
        if self.use_es:
            self.es_client = Elasticsearch([self.elasticsearch_url, ])
        else:
            self.es_client = None
        super().__init__(*args, **kwargs)

    @web.authenticated
    def get(self, task_id: str):
        use_es = self.get_argument('es', type=bool, default=self.use_es)
        task: typing.Union[Task, Hit]
        if use_es:

            try:
                es_client = self.es_client
                if es_client.indices.exists('task'):
                    es_s = Search(using=es_client, index='task')
                    for hit in es_s.query(Match(_id=task_id)):
                        task = hit
                        task.uuid = task_id
                        task.worker = type('worker', (), {})()
                        task.children_raw = task.children
                        task.children = []
                        for re_match in [m for m in re.finditer(r"<Task: \w+([.]\w+)*\((?P<task_uuid>\w+(-\w+)+)\) \w+ clock:\d+>", task.children_raw) if m]:
                            task.children.append(Task(uuid=re_match.group("task_uuid")))
                        task.worker.hostname = task.hostname
                        break
                    else:
                        use_es = False
                else:
                    use_es = False
            except TransportError:
                logger.exception('Issue getting elastic search task data; falling back to in memory')
                use_es = False
        if not use_es:
            events = typing.cast(Events, self.application.events)
            task = get_task_by_id(events, task_id)

        if task is None:
            raise web.HTTPError(404, f"Unknown task '{task_id}'")
        task = self.format_task(task)
        self.render("task.html", task=task)


@total_ordering
class Comparable:
    """
    Compare two objects, one or more of which may be None.  If one of the
    values is None, the other will be deemed greater.
    """

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        try:
            return self.value < other.value
        except TypeError:
            return self.value is None


class DoNotUseElasticSearchHistoryError(Exception):
    pass


class TasksDataTable(BaseHandler):
    def __init__(self, *args, **kwargs):
        if runtime_options.elasticsearch:
            self.query_cache = LRUCache(limit=1000)
            self.use_es = True
            self.elasticsearch_url = runtime_options.elasticsearch_url

            self.es_client = Elasticsearch([self.elasticsearch_url, ])
        else:
            self.query_cache = None
            self.elasticsearch_url = None
            self.use_es = False
        super().__init__(*args, **kwargs)

    # pylint: disable=too-many-locals
    @web.authenticated
    def get(self):
        draw = self.get_argument('draw', type=int)
        start = self.get_argument('start', type=int)
        length = self.get_argument('length', type=int)
        search = self.get_argument('search[value]', type=str)
        use_es = bool(self.use_es)
        column = self.get_argument('order[0][column]', type=int)
        sort_by = self.get_argument(f'columns[{column}][data]', type=str)
        sort_order = self.get_argument('order[0][dir]', type=str) == 'desc'
        total_records = 0
        records_filtered = []
        if use_es:
            use_es, sort_by, filtered_tasks, records_filtered, total_records = self.sort_by_with_elastic_search(search, sort_by, sort_order, start, length)
        if not use_es:
            def key(item):
                return Comparable(getattr(item[1], sort_by))

            self.maybe_normalize_for_sort(self.application.events.state.tasks_by_timestamp(), sort_by)
            sorted_tasks = sorted(
                iter_tasks(self.application.events, search=search),
                key=key,
                reverse=sort_order
            )
            total_records = len(sorted_tasks)

            filtered_tasks = []
            records_filtered = len(sorted_tasks)

            for task in sorted_tasks[start:start + length]:
                task_dict = as_dict(self.format_task(task)[1])
                if task_dict.get('worker'):
                    task_dict['worker'] = task_dict['worker'].hostname

                filtered_tasks.append(task_dict)

        self.write(dict(draw=draw, data=filtered_tasks,
                        recordsTotal=total_records,
                        recordsFiltered=records_filtered))  # bug?

    # pylint: disable=too-many-branches,too-many-locals,too-many-arguments,too-many-statements,too-many-nested-blocks
    def sort_by_with_elastic_search(self, search, sort_by, sort_order, start, length):
        es_client = self.es_client
        filtered_tasks = []
        records_filtered = 0
        use_es = True
        total_records = 0
        try:
            es_s = Search(using=es_client, index='task')
            if search:
                search_terms = parse_search_terms(search or {}, find_time_keys=True)
                if search_terms:
                    if 'es' in search_terms:
                        if search_terms.get('es') == '0':
                            raise DoNotUseElasticSearchHistoryError()
                    if 'args' in search_terms:
                        s_args = search_terms['args']
                        arg_queries = None
                        for s_arg in s_args:
                            if arg_queries is None:
                                arg_queries = Wildcard(args='*'+s_arg+'*')
                            else:
                                arg_queries &= Wildcard(args='*'+s_arg+'*')
                        es_s = es_s.query(arg_queries)
                    if 'kwargs' in search_terms:
                        s_args = search_terms['kwargs']
                        arg_queries = None
                        for s_arg, s_v_arg in s_args.items():
                            if arg_queries is None:
                                arg_queries = Wildcard(kwargs='*' + s_arg + ': ' + s_v_arg + '*')
                            else:
                                arg_queries &= Wildcard(kwargs='*' + s_arg + ': ' + s_v_arg + '*')
                        es_s = es_s.query(arg_queries)
                    if 'result' in search_terms:
                        es_s = es_s.query(Match(result=search_terms['result']))
                    if 'taskname' in search_terms:
                        es_s = es_s.query(Terms(name=search_terms['taskname']))
                    if 'runtime_lt' in search_terms and search_terms['runtime_lt']:
                        es_s = es_s.query(Range(runtime=dict(lt=float(search_terms['runtime_lt']))))
                    if 'runtime_gt' in search_terms and search_terms['runtime_gt']:
                        es_s = es_s.query(Range(runtime=dict(gt=float(search_terms['runtime_gt']))))
                    if 'parent_id' in search_terms:
                        es_s = es_s.filter(Term(parent_id=search_terms['parent_id']))
                    if 'root_id' in search_terms:
                        es_s = es_s.filter(Term(root_id=search_terms['root_id']))
                    if 'received_start' in search_terms:
                        es_s = es_s.filter(Range(received_time=dict(gt=datetime.datetime.utcfromtimestamp(search_terms['received_start']).isoformat())))
                    if 'received_end' in search_terms:
                        es_s = es_s.filter(Range(received_time=dict(lt=datetime.datetime.utcfromtimestamp(search_terms['received_end']).isoformat())))
                    if 'started_start' in search_terms:
                        es_s = es_s.filter(Range(started_time=dict(gt=datetime.datetime.utcfromtimestamp(search_terms['started_start']).isoformat())))
                    if 'started_end' in search_terms:
                        es_s = es_s.filter(Range(started_time=dict(lt=datetime.datetime.utcfromtimestamp(search_terms['started_end']).isoformat())))
                    if 'state' in search_terms:
                        es_s = es_s.query(Terms(state=search_terms['state']))
                    if search_terms.get('uuid'):
                        es_s = es_s.query(Term(**{'_id': search_terms['uuid']}))
                        # if searching by `uuid`, then no need to search by `any`.
                        search_terms.pop('any', None)
                    if 'any' in search_terms:
                        # this is a simple form of the `any` search that flower constructs
                        es_id_query = es_s.filter(Term(**{'_id': search}))
                        id_hits = es_id_query.execute().hits.hits
                        if id_hits:
                            es_s = es_id_query
                        else:
                            es_s = es_s.query(Wildcard(name='*' + search + '*') |
                                              Wildcard(hostname='*' + search + '*'))

            # total_records = es_s.count()
            if sort_by in ('started', 'received', 'succeeded', 'failed', 'revoked', 'timestamp', ):
                sort_by += '_time'
            sorted_tasks = es_s.sort({sort_by: dict(order='asc' if sort_order else 'desc')})
            filtered_tasks = []
            # elastic search window for normal pagination is default at 10000
            # so if we're over 10000, then we need to hand-find the appropriate next value
            # and to do this we have 1 major way:
            # using `search_after` (from this value or a previous search_after)
            # we can efficiently search deeply into elasticsearch
            #
            # If it's our first time and we're going way beyond 10000, then we'll use `search_after`
            # to efficiently get to the proper spot
            # And if we have the previous start already cached, we'll use that to find the next start
            if start + length > 10000:
                total_tries = 5
                cache_value = None
                cache_start = None
                if self.query_cache:
                    for start_offset in range(1, 201):
                        for _ in range(total_tries):
                            cache_value = self.query_cache.get((start - (length * start_offset),
                                                           length, sort_by, sort_order))
                            if cache_value:
                                cache_start = start - (length * start_offset)
                                break
                            time.sleep(0.001)
                        if cache_value:
                            break
                # WIP: handle the case where we grab an older cache key and we need to forward to
                # the current search context appropriately (people spamming the `Next` button faster than we
                # can compute the next one. We can get old ones if they miss the next one)
                # We already retry on the current one, but if we miss out and go earlier, then there could be a bug.
                if cache_value:
                    if cache_start < start - length:
                        # WIP: validate that this will forward us to the correct current start
                        for _ in range(cache_start + length, start - length, length):
                            sorted_tasks = es_s.extra(from_=0,
                                                      size=length, search_after=cache_value).sort(
                                {sort_by: 'asc' if sort_order else 'desc'}, {'_uid': 'desc', }
                            )
                            cache_value = sorted_tasks.execute().hits.hits[-1]['sort']
                    sorted_tasks = es_s.extra(from_=0, size=length, search_after=cache_value).sort(
                        {sort_by: 'asc' if not sort_order else 'desc'}, {'_uid': 'desc', }).execute().hits
                else:
                    last_normal_hits = sorted_tasks.extra(from_=9999, size=1).execute().hits.hits
                    if last_normal_hits:
                        last_hit = last_normal_hits[0]
                        sorted_tasks = es_s.extra(from_=0, size=length,
                                                  search_after=[last_hit['sort'][0],
                                                                'task#' + last_hit['_id']]).sort(
                            {sort_by: 'asc' if sort_order else 'desc'}, {'_uid': 'desc', })
                        hits = sorted_tasks.execute().hits.hits
                        if len(hits) + 10000 < start:
                            # may be a bug in here where we have no hits because of a logic error in here
                            # we could get more efficient by forwarding with a higher `length` until we get
                            # to where we need to be
                            for _ in range(9999+length, start + length, length):
                                hits = sorted_tasks.execute().hits.hits
                                sorted_tasks = es_s.extra(from_=0,
                                                          size=length, search_after=hits[-1]['sort']).sort(
                                    {sort_by: 'asc' if sort_order else 'desc'}, {'_uid': 'desc', }
                                )
                        sorted_tasks = sorted_tasks.execute().hits
            else:
                sorted_tasks = sorted_tasks.extra(from_=start, size=length).execute().hits
            last_task = None
            total_records = sorted_tasks.total
            for task in sorted_tasks.hits:
                task_dict = task.get('_source')
                task_dict['uuid'] = task['_id']
                if task_dict.get('worker'):
                    task_dict['worker'] = task_dict['hostname']
                else:
                    task_dict['worker'] = task_dict.get('hostname')
                filtered_tasks.append(task_dict)
                last_task = task
            records_filtered = sorted_tasks.total
            if start + length > 10000:
                # may be a bug in here --> last_task may be `None` by mistake
                if last_task is not None:
                    self.query_cache[(start, length, sort_by, sort_order)] = last_task.get('sort')
        except TransportError:
            logger.exception('Issue getting elastic search task data; falling back to in memory')
            use_es = False
        except DoNotUseElasticSearchHistoryError:
            use_es = False
        return use_es, sort_by, filtered_tasks, records_filtered, total_records

    @classmethod
    def maybe_normalize_for_sort(cls, tasks, sort_by):
        sort_keys = {'name': str, 'state': str, 'received': float, 'started': float, 'runtime': float}
        if sort_by in sort_keys:
            for _, task in tasks:
                attr_value = getattr(task, sort_by, None)
                if attr_value:
                    try:
                        setattr(task, sort_by, sort_keys[sort_by](attr_value))
                    except TypeError:
                        pass

    @web.authenticated
    def post(self):
        return self.get()

    def format_task(self, task):
        uuid, args = task
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            try:
                args = custom_format_task(copy.copy(args))
            except Exception:
                logger.exception("Failed to format '%s' task", uuid)
        return uuid, args


class TasksView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp

        time_setting = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.timezone:
            time_setting += '-' + str(capp.conf.timezone)

        self.render(
            "tasks.html",
            tasks=[],
            columns=app.options.tasks_columns,
            time=time_setting,
        )
