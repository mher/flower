import ast
import datetime
import heapq
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from kombu.utils.encoding import safe_str

SEARCH_FIELDS = frozenset({'name', 'state', 'worker', 'args', 'kwargs', 'result'})
EXACT_FIELDS = frozenset({'state'})
EXACT_INDEX_FIELDS = frozenset({'name', 'state', 'worker'})
MIN_SUBSTRING_LENGTH = 3
MAX_QUERY_LENGTH = 2048
MAX_QUERY_TOKENS = 128
MAX_QUERY_DEPTH = 5


class QuerySyntaxError(ValueError):
    def __init__(self, message, position=None):
        self.message = message
        self.position = position
        detail = message if position is None else f'{message} at position {position}'
        super().__init__(f'{detail}.')


@dataclass(frozen=True)
class MatchAll:
    pass


@dataclass(frozen=True)
class Term:
    field: str | None
    value: str


@dataclass(frozen=True)
class And:
    children: tuple


@dataclass(frozen=True)
class Or:
    children: tuple


@dataclass(frozen=True)
class _Token:
    kind: str
    value: str
    position: int


def _append_token(tokens, kind, value, position):
    tokens.append(_Token(kind, value, position))
    if len(tokens) > MAX_QUERY_TOKENS:
        raise QuerySyntaxError(f'Query exceeds {MAX_QUERY_TOKENS} tokens')


# pylint: disable=too-many-branches
def _tokenize(raw_query):
    tokens = []
    index = 0
    length = len(raw_query)

    while index < length:
        if raw_query[index].isspace():
            index += 1
            continue

        position = index
        if raw_query[index] == '(':
            _append_token(tokens, 'LPAREN', '(', position)
            index += 1
            continue
        if raw_query[index] == ')':
            _append_token(tokens, 'RPAREN', ')', position)
            index += 1
            continue

        value = []
        quoted = False
        in_quote = False
        while index < length:
            char = raw_query[index]
            if char == '\\' and index + 1 < length and raw_query[index + 1] in ('"', '\\'):
                value.append(raw_query[index + 1])
                index += 2
                continue
            if char == '"':
                quoted = True
                in_quote = not in_quote
                index += 1
                continue
            if not in_quote and (char.isspace() or char in '()'):
                break
            value.append(char)
            index += 1

        if in_quote:
            raise QuerySyntaxError('Unterminated quoted phrase', position)

        token_value = ''.join(value)
        if not token_value:
            raise QuerySyntaxError('Empty search term', position)
        if not quoted and token_value in ('AND', 'OR'):
            kind = token_value
        elif not quoted and token_value == 'NOT':
            raise QuerySyntaxError('NOT is not supported', position)
        else:
            kind = 'TERM'
        _append_token(tokens, kind, token_value, position)

    tokens.append(_Token('EOF', '', length))
    return tokens


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def advance(self):
        token = self.current
        self.index += 1
        return token

    def parse(self):
        if self.current.kind == 'EOF':
            return MatchAll()
        expression = self.parse_or(0)
        if self.current.kind != 'EOF':
            raise QuerySyntaxError(f'Unexpected {self.current.value!r}', self.current.position)
        return expression

    def parse_or(self, depth):
        children = [self.parse_and(depth)]
        while self.current.kind == 'OR':
            operator = self.advance()
            if self.current.kind in ('EOF', 'RPAREN', 'AND', 'OR'):
                raise QuerySyntaxError('OR must be followed by a search term', operator.position)
            children.append(self.parse_and(depth))
        return _combine(Or, children)

    def parse_and(self, depth):
        children = [self.parse_primary(depth)]
        while self.current.kind not in ('EOF', 'RPAREN', 'OR'):
            if self.current.kind == 'AND':
                operator = self.advance()
                if self.current.kind in ('EOF', 'RPAREN', 'AND', 'OR'):
                    raise QuerySyntaxError(
                        'AND must be followed by a search term', operator.position)
            elif self.current.kind not in ('TERM', 'LPAREN'):
                raise QuerySyntaxError(f'Unexpected {self.current.value!r}', self.current.position)
            children.append(self.parse_primary(depth))
        return _combine(And, children)

    def parse_primary(self, depth):
        token = self.current
        if token.kind == 'LPAREN':
            if depth >= MAX_QUERY_DEPTH:
                raise QuerySyntaxError(
                    f'Query nesting exceeds {MAX_QUERY_DEPTH} levels', token.position)
            self.advance()
            if self.current.kind == 'RPAREN':
                raise QuerySyntaxError('Empty group', token.position)
            expression = self.parse_or(depth + 1)
            if self.current.kind != 'RPAREN':
                raise QuerySyntaxError('Missing closing parenthesis', token.position)
            self.advance()
            return expression
        if token.kind != 'TERM':
            raise QuerySyntaxError('Expected a search term', token.position)
        self.advance()
        return _parse_term(token)


def _combine(node_type, children):
    flattened = []
    for child in children:
        candidates = child.children if isinstance(child, node_type) else (child,)
        for candidate in candidates:
            if candidate not in flattened:
                flattened.append(candidate)
    if len(flattened) == 1:
        return flattened[0]
    return node_type(tuple(flattened))


def _parse_term(token):
    field: str | None = None
    value = token.value
    if ':' in value:
        candidate, candidate_value = value.split(':', 1)
        if candidate.casefold() in SEARCH_FIELDS:
            field = candidate.casefold()
            value = candidate_value
    if field is None and value.startswith('-'):
        raise QuerySyntaxError("Negation with '-' is not supported", token.position)
    if not value:
        raise QuerySyntaxError('Search qualifier requires a value', token.position)
    is_exact = (field in EXACT_FIELDS) or (field == 'kwargs' and '=' in value)
    if not is_exact and len(value.strip()) < MIN_SUBSTRING_LENGTH:
        raise QuerySyntaxError(
            f'Substring search terms must contain at least '
            f'{MIN_SUBSTRING_LENGTH} characters', token.position)
    return Term(field, value)


def parse_query(raw_query):
    query = safe_str(raw_query or '').strip()
    if len(query) > MAX_QUERY_LENGTH:
        raise QuerySyntaxError(f'Query exceeds {MAX_QUERY_LENGTH} characters')
    return _parse_query_cached(query)


@lru_cache(maxsize=512)
def _parse_query_cached(query):
    return _Parser(_tokenize(query)).parse()


def _normalize(value):
    if value is None:
        return ''
    return safe_str(value).casefold()


def _worker_name(task):
    worker = getattr(task, 'worker', None)
    return getattr(worker, 'hostname', worker) or ''


def _kwargs_pairs(value):
    mapping = value if isinstance(value, dict) else None
    if mapping is None and isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, dict):
            mapping = parsed
    if not mapping:
        return frozenset()
    return frozenset(
        f'{_normalize(key)}={_normalize(item)}'
        for key, item in mapping.items()
    )


def _kwargs_query_pair(value):
    if '=' not in value:
        return None
    key, item = value.split('=', 1)
    return f'{key.strip()}={item.strip()}'


class SearchDocument:
    __slots__ = (
        'all_text',
        'args',
        'kwargs',
        'kwargs_pairs',
        'name',
        'result',
        'state',
        'worker',
    )

    # pylint: disable=too-many-arguments
    def __init__(self, name, state, worker, args, kwargs, result,
                 all_text, kwargs_pairs):
        self.name = name
        self.state = state
        self.worker = worker
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.all_text = all_text
        self.kwargs_pairs = kwargs_pairs

    @classmethod
    def from_task(cls, task):
        uuid = _normalize(getattr(task, 'uuid', ''))
        name = _normalize(getattr(task, 'name', ''))
        state = _normalize(getattr(task, 'state', ''))
        worker = _normalize(_worker_name(task))
        args = _normalize(getattr(task, 'args', ''))
        kwargs = _normalize(getattr(task, 'kwargs', ''))
        result = _normalize(getattr(task, 'result', ''))
        return cls(
            name,
            state,
            worker,
            args,
            kwargs,
            result,
            f'{uuid}\x00{name}\x00{state}\x00{worker}\x00{args}\x00{kwargs}\x00{result}',
            _kwargs_pairs(getattr(task, 'kwargs', None)))


@dataclass(frozen=True)
class SearchPage:
    task_ids: list
    filtered_count: int
    total_count: int


class TaskSearchEngine:
    def __init__(self):
        self.documents = {}
        self.exact_postings = {
            field: defaultdict(set)
            for field in EXACT_INDEX_FIELDS
        }
        self.kwargs_postings = defaultdict(set)

    def _clear(self):
        self.documents.clear()
        for index in self.exact_postings.values():
            index.clear()
        self.kwargs_postings.clear()

    def rebuild(self, tasks):
        self._clear()
        for _, task in tasks:
            task_id = safe_str(getattr(task, 'uuid', ''))
            if task_id:
                self._index(task_id, task)

    def upsert(self, task):
        task_id = safe_str(getattr(task, 'uuid', ''))
        if not task_id:
            return
        self.remove(task_id)
        self._index(task_id, task)

    def _index(self, task_id, task):
        document = SearchDocument.from_task(task)
        self.documents[task_id] = document

        for field, index in self.exact_postings.items():
            value = getattr(document, field)
            if value:
                index[value].add(task_id)
        for pair in document.kwargs_pairs:
            self.kwargs_postings[pair].add(task_id)

    def remove(self, task_id):
        document = self.documents.pop(task_id, None)
        if document is None:
            return
        for field, index in self.exact_postings.items():
            value = getattr(document, field)
            if value:
                _remove_posting(index, value, task_id)
        for pair in document.kwargs_pairs:
            _remove_posting(self.kwargs_postings, pair, task_id)

    def matching_ids(self, query, candidates=None):
        return self._evaluate(parse_query(query), candidates)

    # pylint: disable=too-many-arguments,too-many-locals
    def search(self, tasks, query='', *, task_type=None, worker=None, state=None,
               received_start=None, received_end=None, started_start=None,
               started_end=None, sort_by=None, descending=False, offset=0,
               limit=None, root_id=None, parent_id=None, runtime_lt=None,
               runtime_gt=None):
        task_map = getattr(tasks, 'data', tasks)
        task_ids = set(self.documents)
        task_ids.intersection_update(task_map.keys())

        if task_type:
            task_ids.intersection_update(
                self.exact_postings['name'].get(_normalize(task_type), ()))
        if worker:
            task_ids.intersection_update(
                self.exact_postings['worker'].get(_normalize(worker), ()))
        if state:
            task_ids.intersection_update(
                self.exact_postings['state'].get(_normalize(state), ()))
        if root_id:
            task_ids = {tid for tid in task_ids
                        if task_map.get(tid) and
                        getattr(task_map[tid], 'root_id', None) == root_id}
        if parent_id:
            task_ids = {tid for tid in task_ids
                        if task_map.get(tid) and
                        getattr(task_map[tid], 'parent_id', None) == parent_id}
        if runtime_lt is not None:
            task_ids = {tid for tid in task_ids
                        if task_map.get(tid) and
                        getattr(task_map[tid], 'runtime', None) is not None and
                        float(runtime_lt) > task_map[tid].runtime}
        if runtime_gt is not None:
            task_ids = {tid for tid in task_ids
                        if task_map.get(tid) and
                        getattr(task_map[tid], 'runtime', None) is not None and
                        float(runtime_gt) < task_map[tid].runtime}

        if received_start is not None or received_end is not None:
            task_ids = {
                task_id for task_id in task_ids
                if _task_in_time_range(
                    task_map[task_id], received_start, received_end)
            }
        if started_start is not None or started_end is not None:
            task_ids = {
                task_id for task_id in task_ids
                if _task_in_time_range(
                    task_map[task_id], started_start, started_end,
                    attr='started')
            }

        task_ids = self.matching_ids(query, task_ids)

        filtered_count = len(task_ids)
        ordered_ids = list(task_ids)
        offset = max(offset, 0)
        end = None if limit is None else offset + max(limit, 0)
        if sort_by:
            def sort_key_func(task_id):
                return _task_sort_key(task_map[task_id], sort_by, task_id)
        else:
            def sort_key_func(task_id):
                return (
                    getattr(task_map[task_id], 'timestamp', None) or 0,
                    task_id)
            descending = True

        if end is not None and end < filtered_count:
            select = heapq.nlargest if descending else heapq.nsmallest
            ordered_ids = select(end, ordered_ids, key=sort_key_func)
        else:
            ordered_ids.sort(key=sort_key_func, reverse=descending)
        return SearchPage(
            ordered_ids[offset:end], filtered_count, len(task_map))

    def _evaluate(self, expression, candidates=None):
        universe = set(self.documents) if candidates is None else candidates
        if isinstance(expression, MatchAll):
            return universe.copy()
        if isinstance(expression, Term):
            return self._term_ids(expression, universe)
        if isinstance(expression, And):
            result = universe.copy()
            children = sorted(expression.children, key=self._estimate_size)
            for child in children:
                result = self._evaluate(child, result)
                if not result:
                    break
            return result
        if isinstance(expression, Or):
            result = set()
            for child in expression.children:
                result.update(self._evaluate(child, universe))
            return result
        raise TypeError(f'Unsupported search expression: {type(expression)!r}')

    def _term_ids(self, term, candidates):
        value = _normalize(term.value)
        if term.field in EXACT_FIELDS:
            result = set(self.exact_postings[term.field].get(value, ()))
            result.intersection_update(candidates)
            return result
        kwargs_pair = _kwargs_query_pair(value) if term.field == 'kwargs' else None
        if kwargs_pair is not None:
            result = set(self.kwargs_postings.get(kwargs_pair, ()))
            result.intersection_update(candidates)
            return result
        field = term.field or 'all'
        return {
            task_id for task_id in candidates
            if value in (
                self.documents[task_id].all_text
                if field == 'all'
                else getattr(self.documents[task_id], field))
        }

    def _estimate_size(self, expression):
        if isinstance(expression, Term):
            value = _normalize(expression.value)
            if expression.field in EXACT_FIELDS:
                return len(self.exact_postings[expression.field].get(value, ())), 0
            kwargs_pair = (
                _kwargs_query_pair(value)
                if expression.field == 'kwargs' else None)
            if kwargs_pair is not None:
                return len(self.kwargs_postings.get(kwargs_pair, ())), 0
            return len(self.documents), -len(value)
        if isinstance(expression, And):
            return min(
                (self._estimate_size(child) for child in expression.children),
                default=(len(self.documents), 0))
        if isinstance(expression, Or):
            estimates = [
                self._estimate_size(child)[0]
                for child in expression.children
            ]
            return min(sum(estimates), len(self.documents)), 1
        return len(self.documents), 1


def _remove_posting(index, value, task_id):
    task_ids = index.get(value)
    if task_ids is None:
        return
    task_ids.discard(task_id)
    if not task_ids:
        del index[value]


def _task_in_time_range(task, time_start, time_end, attr='received'):
    value = getattr(task, attr, None)
    if time_start is not None and value is not None and value < time_start:
        return False
    return time_end is None or value is None or value <= time_end


def _task_sort_key(task, sort_by, task_id):
    value = getattr(task, sort_by, None)
    if value is None:
        return False, '', task_id
    if sort_by in ('received', 'started', 'runtime'):
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
    else:
        value = _normalize(value)
    return True, value, task_id


# Elasticsearch-specific search term parsing (from feature branch)
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
            if 'kwargs' not in parsed_search:
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
            if query_part.startswith('received_start:'):
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
