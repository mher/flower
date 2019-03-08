import re
import datetime
from datetime import timezone

from kombu.utils.encoding import safe_str

from .template import humanize

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)


def parse_search_terms(raw_search_value):
    search_regexp = r'(?:[^\s,"]|"(?:\\.|[^"])*")+'  # splits by space, ignores space in quotes
    if not raw_search_value:
        return {}
    parsed_search = {}
    for query_part in re.findall(search_regexp, raw_search_value):
        if not query_part:
            continue
        if query_part.startswith('result:'):
            parsed_search['result'] = preprocess_search_value(query_part[len('result:'):])
        elif query_part.startswith('args:'):
            if 'args' not in parsed_search:
                parsed_search['args'] = []
            parsed_search['args'].append(preprocess_search_value(query_part[len('args:'):]))
        elif query_part.startswith('kwargs:'):
            if 'kwargs'not in parsed_search:
                parsed_search['kwargs'] = {}
            key, value = [p.strip() for p in query_part[len('kwargs:'):].split('=')]
            parsed_search['kwargs'][key] = preprocess_search_value(value)
        elif query_part.startswith('state'):
            if 'state' not in parsed_search:
                parsed_search['state'] = []
            parsed_search['state'].append(preprocess_search_value(query_part[len('state:'):]))
        elif query_part.startswith('date'):
            if 'date' not in parsed_search:
                date = preprocess_search_value(query_part[len('date:'):])
                try:
                    date = datetime.datetime.strptime(date, "%Y-%m-%d")
                    date = date.replace(tzinfo=timezone.utc)
                    parsed_search['date'] = (date - _EPOCH).total_seconds()
                except ValueError:
                    pass
        else:
            parsed_search['any'] = preprocess_search_value(query_part)
    return parsed_search


def satisfies_search_terms(task, search_terms):
    any_value_search_term = search_terms.get('any')
    result_search_term = search_terms.get('result')
    args_search_terms = search_terms.get('args')
    kwargs_search_terms = search_terms.get('kwargs')
    state_search_terms = search_terms.get('state')
    date_search_terms = search_terms.get('date')

    if not any([any_value_search_term, result_search_term, args_search_terms, kwargs_search_terms, state_search_terms, date_search_terms]):
        return True

    terms = [
        state_search_terms and task.state in state_search_terms,
        any_value_search_term and any_value_search_term in '|'.join(
            filter(None, [task.name, task.uuid, task.state,
                          task.worker.hostname if task.worker else None,
                          task.args, task.kwargs, safe_str(task.result)])),
        result_search_term and result_search_term in task.result,
        kwargs_search_terms and all(
            stringified_dict_contains_value(k, v, task.kwargs) for k, v in kwargs_search_terms.items()
        ),
        args_search_terms and task_args_contains_search_args(task.args, args_search_terms),
        date_search_terms and task.started and task_started_in_date(task.started, date_search_terms),
    ]
    return any(terms)


def stringified_dict_contains_value(key, value, str_dict):
    """Checks if dict in for of string like "{'test': 5}" contains
    key/value pair. This works faster, then creating actual dict
    from string since this operation is called for each task in case
    of kwargs search."""
    value = str(value)
    try:
        # + 3 for key right quote, one for colon and one for space
        key_index = str_dict.index(key) + len(key) + 3
    except ValueError:
        return False
    try:
        comma_index = str_dict.index(',', key_index)
    except ValueError:
        # last value in dict
        comma_index = str_dict.index('}', key_index)
    return str(value) == str_dict[key_index:comma_index].strip('"\'')


def preprocess_search_value(raw_value):
    return raw_value.strip('" ') if raw_value else ''


def task_args_contains_search_args(task_args, search_args):
    return all(a in task_args for a in search_args)


def task_started_in_date(start, date):
    start = datetime.datetime.strptime(humanize(start, 'time'), '%Y-%m-%d %H:%M:%S.%f %Z')
    date = datetime.datetime.strptime(humanize(date, 'time'), '%Y-%m-%d %H:%M:%S.%f %Z')
    return start.date() == date.date()
