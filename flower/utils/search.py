import re


def parse_search_terms(raw_search_value):
    search_regexp = r'(?:([^=]+)=)?([^=]+)(?:,|$)'  # parses value or key-value pairs, delimited by comma
    if not raw_search_value:
        return {}
    raw_search_value = raw_search_value.strip()
    parsed_search = {}
    parsed_search_terms = dict(re.findall(search_regexp, raw_search_value))
    if '' in parsed_search_terms:  # asked for args, not kwargs
        parsed_search['any'] = list(parsed_search_terms.values())[0]
    else:
        if 'result' in parsed_search_terms:
            parsed_search['result'] = parsed_search_terms.pop('result')
        if parsed_search_terms:
            parsed_search['kwargs'] = parsed_search_terms
    return parsed_search


def satisfies_search_terms(task, any_value_search_term, result_search_term, kwargs_search_terms):
    if not any([any_value_search_term, result_search_term, kwargs_search_terms]):
        return True
    terms = [
        any_value_search_term and any_value_search_term in '|'.join([task.args, task.kwargs, str(task.result)]),
        result_search_term and result_search_term in task.result,
        kwargs_search_terms and all(
            stringified_dict_contains_value(k, v, task.kwargs) for k, v in kwargs_search_terms.items()
        )
    ]
    return any(terms)


def stringified_dict_contains_value(key, value, str_dict):
    """
        Checks if dict in for of string like "{'test': 5}" contains key/value pair.

        This works faster, then creating actual dict from string since this operation is called
        for each task in case of kwargs search.
    """
    value = str(value)
    try:
        key_index = str_dict.index(key) + len(key)
    except ValueError:  # key not found
        return False
    try:
        comma_index = str_dict.index(',', key_index)
    except ValueError:  # last value in dict
        comma_index = str_dict.index('}', key_index)
    # TODO: will match for any string, containing value; fix that
    return str(value) in str_dict[key_index:comma_index]
