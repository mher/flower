import ast
import datetime
import json
import time

from .search import parse_search_terms, satisfies_search_terms


# pylint: disable=too-many-branches,too-many-locals,too-many-arguments
def iter_tasks(events, limit=None, offset=0, type=None, worker=None, state=None,
               sort_by=None, received_start=None, received_end=None,
               started_start=None, started_end=None, search=None):
    i = 0
    tasks = events.state.tasks_by_timestamp()
    if sort_by is not None:
        tasks = sort_tasks(tasks, sort_by)

    def convert(x):
        return time.mktime(datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple())

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
        if i >= offset:
            yield uuid, task
        i += 1
        if limit is not None:
            if i == limit + offset:
                break


sort_keys = {'name': str, 'state': str, 'received': float, 'started': float}


def sort_tasks(tasks, sort_by):
    assert sort_by.lstrip('-') in sort_keys
    reverse = False
    if sort_by.startswith('-'):
        sort_by = sort_by.lstrip('-')
        reverse = True
    yield from sorted(
            tasks,
            key=lambda x: getattr(x[1], sort_by) or sort_keys[sort_by](),
            reverse=reverse)


def get_task_by_id(events, task_id):
    return events.state.tasks.get(task_id)


def as_dict(task):
    return task.as_dict()


# Upper bound on the size of a stored args/kwargs string we are willing to
# parse. Celery truncates event args far below this; anything larger is not
# a legitimate task representation and is rejected before parsing.
MAX_ARG_LENGTH = 65536


def _parse_literal(value, kind):
    """
    Parse a string holding a JSON value or a Python literal (the two formats
    celery events use for task args/kwargs) into a Python value.

    Only ``json.loads`` and ``ast.literal_eval`` are used, so no code is ever
    executed. Raises ValueError for anything that is not a plain literal,
    including truncated reprs such as ``'(1, 2, ...'``.
    """
    if len(value) > MAX_ARG_LENGTH:
        raise ValueError(f"Task {kind} too long to parse ({len(value)} bytes)")
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    except (MemoryError, RecursionError) as exc:
        raise ValueError(f"Could not parse task {kind}: {value!r}") from exc
    try:
        return ast.literal_eval(value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
        raise ValueError(f"Could not parse task {kind}: {value!r}") from exc


def _reject_truncated(obj, kind):
    """
    Reject values truncated by celery.

    Celery stores event args/kwargs via saferepr, which truncates long
    strings by cutting them and appending '...' inside the quotes, so a
    truncated repr like "(7, 'Bearer...')" still parses cleanly. Refuse
    such values rather than reapply a task with corrupted arguments.
    A legitimate string ending in '...' is indistinguishable from a
    truncated one, so it is rejected too.
    """
    if isinstance(obj, str):
        if obj.endswith('...'):
            raise ValueError(f"Task {kind} appear truncated by celery: {obj!r}")
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            _reject_truncated(item, kind)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            _reject_truncated(key, kind)
            _reject_truncated(value, kind)


def parse_args(args):
    """
    Parse the string representation of a task's positional arguments
    into a list.

    Raises ValueError if the string cannot be restored to the original
    arguments (e.g. it was truncated by celery), so callers never reapply
    a task with wrong arguments.
    """
    if not args:
        return []
    parsed = _parse_literal(args, 'args')
    if isinstance(parsed, tuple):
        parsed = list(parsed)
    if not isinstance(parsed, list):
        raise ValueError(f"Task args must be a list or tuple: {args!r}")
    _reject_truncated(parsed, 'args')
    return parsed


def parse_kwargs(kwargs):
    """
    Parse the string representation of a task's keyword arguments
    into a dict.

    Raises ValueError if the string cannot be restored to the original
    keyword arguments.
    """
    if not kwargs:
        return {}
    parsed = _parse_literal(kwargs, 'kwargs')
    if not isinstance(parsed, dict):
        raise ValueError(f"Task kwargs must be a dict: {kwargs!r}")
    _reject_truncated(parsed, 'kwargs')
    return parsed


def make_json_serializable(obj):
    """
    Recursively convert parsed argument values to JSON-serializable types.

    Raises TypeError for values with no faithful JSON equivalent (sets,
    bytes, non-string dict keys, ...) so callers fail loudly instead of
    reapplying a task with arguments of the wrong type. Tuples become
    lists because that is what the original task received from the JSON
    serializer anyway.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise TypeError(f"Dict key {key!r} is not JSON serializable")
            result[key] = make_json_serializable(value)
        return result
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Value of type {type(obj).__name__} is not JSON serializable: {obj!r}")
