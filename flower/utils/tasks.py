from __future__ import absolute_import

import datetime
import time

from .search import satisfies_search_terms, parse_search_terms

from celery.events.state import Task


def iter_tasks(events, limit=None, type=None, worker=None, state=None,
               sort_by=None, received_start=None, received_end=None,
               started_start=None, started_end=None, search=None):
    i = 0
    tasks = events.state.tasks_by_timestamp()
    if sort_by is not None:
        tasks = sort_tasks(tasks, sort_by)
    convert = lambda x: time.mktime(
        datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple()
    )
    search_terms = parse_search_terms(search or {})

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
        if not satisfies_search_terms(task, search_terms):
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
    for task in sorted(
            tasks,
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


def as_dict(task):
    result = dict()

    # for celery <3.8, we can use task._defaults, for celery
    # 3.9 we use .as_dict(), and for later, we use task._info_fields
    # we should be using .as_dict() for 4.0 as well, but it's broken

    if hasattr(Task, '_info_fields'):
        for key in list(task._info_fields) + list(task._fields):
            value = getattr(task, key, None)

            # children is a WeakSet, if we don't do this
            # then the resulting dict is not serializable
            if key == 'children':
                value = value.__repr__()

            result[key] = value
    elif hasattr(Task, 'as_dict'):
        result = task.as_dict()
    else:
        result = task.info(fields=task._defaults.keys())

    return result
