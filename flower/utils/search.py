import datetime
import re
import time

from kombu.utils.encoding import safe_str

# pylint: disable=too-many-branches,too-many-statements
def parse_search_terms(raw_search_value, find_time_keys=False):
    search_regexp = r'(?:[^\s,"]|"(?:\\.|[^"])*")+'  # splits by space, ignores space in quotes
    if not raw_search_value:
        return {}
    parsed_search = {}
    for query_part in re.findall(search_regexp, raw_search_value):
        if not query_part:
            continue
        find_any = True
        if query_part.startswith('result:'):
            parsed_search['result'] = preprocess_search_value(query_part[len('result:'):])
        elif query_part.startswith('args:'):
            if 'args' not in parsed_search:
                parsed_search['args'] = []
            parsed_search['args'].append(preprocess_search_value(query_part[len('args:'):]))
        elif query_part.startswith('taskname:'):
            if 'taskname' not in parsed_search:
                parsed_search['taskname'] = []
            parsed_search['taskname'].append(preprocess_search_value(query_part[len('taskname:'):]))
        elif query_part.startswith('kwargs:'):
            if 'kwargs'not in parsed_search:
                parsed_search['kwargs'] = {}
            try:
                key, value = [p.strip() for p in query_part[len('kwargs:'):].split('=')]
            except ValueError:
                continue
            parsed_search['kwargs'][key] = preprocess_search_value(value)
        elif query_part.startswith('state'):
            if 'state' not in parsed_search:
                parsed_search['state'] = []
            parsed_search['state'].append(preprocess_search_value(query_part[len('state:'):]))
        elif query_part.startswith('es:'):
            parsed_search['es'] = preprocess_search_value(query_part[len('es:'):])
        elif query_part.startswith('uuid:'):
            parsed_search['uuid'] = preprocess_search_value(query_part[len('uuid:'):])
        elif query_part.startswith('runtime_lt:'):
            parsed_search['runtime_lt'] = preprocess_search_value(query_part[len('runtime_lt:'):])
        elif query_part.startswith('runtime_gt:'):
            parsed_search['runtime_gt'] = preprocess_search_value(query_part[len('runtime_gt:'):])
        elif query_part.startswith('root_id:'):
            parsed_search['root_id'] = preprocess_search_value(query_part[len('root_id:'):])
        elif query_part.startswith('parent_id:'):
            parsed_search['parent_id'] = preprocess_search_value(query_part[len('parent_id:'):])
        if parsed_search:
            find_any = False
        if find_time_keys:
            def convert(x):
                try:
                    if x.count(":") == 2:
                        if x.count("."):
                            # does not return fractional second information, but at least
                            # we can "support" it being passed in, as opposed to ignoring it
                            return time.mktime(
                                datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f').timetuple()
                            )

                        return time.mktime(
                            datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S').timetuple()
                        )
                    return time.mktime(
                        datetime.datetime.strptime(x, '%Y-%m-%d %H:%M').timetuple()
                    )
                except ValueError:
                    return ""
            if query_part.startswith('received_start'):
                received_start = preprocess_search_value(query_part[len('received_start:'):])
                if received_start:
                    parsed_search['received_start'] = convert(received_start)
                    find_any = False
            if query_part.startswith('received_end'):
                received_end = preprocess_search_value(query_part[len('received_end:'):])
                if received_end:
                    parsed_search['received_end'] = convert(received_end)
                    find_any = False
            if query_part.startswith('started_start'):
                started_start = preprocess_search_value(query_part[len('started_start:'):])
                if started_start:
                    parsed_search['started_start'] = convert(started_start)
                    find_any = False
            if query_part.startswith('started_end'):
                started_end = preprocess_search_value(query_part[len('started_end:'):])
                if started_end:
                    parsed_search['started_end'] = convert(started_end)
                    find_any = False
        if find_any:
            parsed_search['any'] = preprocess_search_value(query_part)
    return parsed_search


def satisfies_search_terms(task, search_terms):
    any_value_search_term = search_terms.get('any')
    result_search_term = search_terms.get('result')
    task_name_search_term = search_terms.get('taskname')
    args_search_terms = search_terms.get('args')
    kwargs_search_terms = search_terms.get('kwargs')
    state_search_terms = search_terms.get('state')
    runtime_lt = search_terms.get("runtime_lt")
    runtime_gt = search_terms.get("runtime_gt")

    activated_terms = [
        any_value_search_term, result_search_term,
        task_name_search_term, args_search_terms,
        kwargs_search_terms, state_search_terms,
        runtime_lt, runtime_gt,
    ]
    if not any(activated_terms):
        return True

    terms = [
        state_search_terms and task.state in state_search_terms,
        any_value_search_term and any_value_search_term in '|'.join(
            filter(None, [task.name, task.uuid, task.state,
                          task.worker.hostname if task.worker else None,
                          task.args, task.kwargs, safe_str(task.result)])),
        result_search_term and task.result and result_search_term in task.result,
        kwargs_search_terms and all(
            stringified_dict_contains_value(k, v, task.kwargs) for k, v in kwargs_search_terms.items()
        ),
        args_search_terms and task_args_contains_search_args(task.args, args_search_terms),
        runtime_lt is not None and task.runtime is not None and float(runtime_lt) > task.runtime,
        runtime_gt is not None and task.runtime is not None and float(runtime_gt) < task.runtime,
    ]
    return any(terms)


def stringified_dict_contains_value(key, value, str_dict):
    """Checks if dict in for of string like "{'test': 5}" contains
    key/value pair. This works faster, then creating actual dict
    from string since this operation is called for each task in case
    of kwargs search."""
    if not str_dict:
        return False
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
    if not task_args:
        return False
    return all(a in task_args for a in search_args)
