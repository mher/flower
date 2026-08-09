import ast
import heapq
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
    field: str
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
    field = None
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
    is_exact = field in EXACT_FIELDS or (field == 'kwargs' and '=' in value)
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
    __slots__ = ('name', 'state', 'worker', 'args', 'kwargs',
                 'result', 'all_text', 'kwargs_pairs')

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
            '\0'.join((uuid, name, state, worker, args, kwargs, result)),
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
               limit=None):
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

        if any(value is not None for value in (
                received_start, received_end, started_start, started_end)):
            task_ids = {
                task_id for task_id in task_ids
                if _task_in_time_range(
                    task_map[task_id], received_start, received_end,
                    started_start, started_end)
            }

        task_ids = self.matching_ids(query, task_ids)

        filtered_count = len(task_ids)
        ordered_ids = list(task_ids)
        offset = max(offset, 0)
        end = None if limit is None else offset + max(limit, 0)
        if sort_by:
            def key(task_id):
                return _task_sort_key(task_map[task_id], sort_by, task_id)
        else:
            def key(task_id):
                return (
                    getattr(task_map[task_id], 'timestamp', None) or 0,
                    task_id)
            descending = True

        if end is not None and end < filtered_count:
            select = heapq.nlargest if descending else heapq.nsmallest
            ordered_ids = select(end, ordered_ids, key=key)
        else:
            ordered_ids.sort(key=key, reverse=descending)
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


# pylint: disable=too-many-return-statements
def _task_in_time_range(task, received_start, received_end,
                        started_start, started_end):
    received = getattr(task, 'received', None)
    started = getattr(task, 'started', None)
    if received_start is not None and received is not None and received < received_start:
        return False
    if received_end is not None and received is not None and received > received_end:
        return False
    if started_start is not None and started is not None and started < started_start:
        return False
    if started_end is not None and started is not None and started > started_end:
        return False
    return True


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
