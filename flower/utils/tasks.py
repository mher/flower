import datetime
import time
from celery.events.state import Task


def iter_tasks(events, limit=None, type=None, worker=None, state=None,
               sort_by=None, received_start=None, received_end=None,
               started_start=None, started_end=None):
    i = 0
    tasks = events.state.tasks_by_timestamp()
    if sort_by is not None:
        tasks = sort_tasks(tasks, sort_by)
    convert = lambda x: time.mktime(
        datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple()
    )

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

        yield uuid, task
        i += 1
        if i == limit:
            break


def sort_tasks(tasks, sort_by):
    assert sort_by.lstrip('-') in ('name', 'state', 'received', 'started')
    reverse = False
    if sort_by.startswith('-'):
        sort_by = sort_by.lstrip('-')
        reverse = True
    for task in sorted(tasks, key=lambda x: getattr(x[1], sort_by), reverse=reverse):
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
