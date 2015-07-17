from __future__ import absolute_import

import datetime
import time

from celery.events.state import Task

from .search import satisfies_search_terms


def iter_tasks(events, limit=None, type=None, worker=None, state=None,
               sort_by=None, received_start=None, received_end=None,
               started_start=None, started_end=None, search_terms=None):
    i = 0
    tasks = events.state.tasks_by_timestamp()
    if sort_by is not None:
        tasks = sort_tasks(tasks, sort_by)
    convert = lambda x: time.mktime(
        datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple()
    )
    any_value_search_term = search_terms.get('any', None)
    result_search_term = search_terms.get('result', None)
    args_search_terms = search_terms.get('args', None)
    kwargs_search_terms = search_terms.get('kwargs', None)

    for uuid, task in tasks:
        if type and task.name != type:
            continue
        if worker and task.worker and task.worker.hostname != worker:
            continue
        if state and task.state != state:
            continue
        if received_start and task.received and\
                task.received < convert(received_start):
            continue
        if received_end and task.received and\
                task.received > convert(received_end):
            continue
        if started_start and task.started and\
                task.started < convert(started_start):
            continue
        if started_end and task.started and\
                task.started > convert(started_end):
            continue
        if not satisfies_search_terms(task, any_value_search_term, result_search_term, args_search_terms, kwargs_search_terms):
            continue
        yield uuid, task
        i += 1
        if i == limit:
            break

sort_keys = {'name': str, 'state': str, 'received': float, 'started': float}
def sort_tasks(tasks, sort_by):
    assert sort_by.lstrip('-') in sort_keys
    reverse = False
    if sort_by.startswith('-'):
        sort_by = sort_by.lstrip('-')
        reverse = True
    for task in sorted(tasks,
                       key=lambda x: getattr(x[1], sort_by) or sort_keys[sort_by](),
                       reverse=reverse):
        yield task


def get_task_by_id(events, task_id):
    if hasattr(Task, '_fields'):  # Old version
        return events.state.tasks.get(task_id)
    else:
        _fields = Task._defaults.keys()
        task = events.state.tasks.get(task_id)
        if task is not None:
            task._fields = _fields
        return task
