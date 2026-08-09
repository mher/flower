import pickle
import time
import unittest
from types import SimpleNamespace

from celery.events import Event

from flower.events import EventsState
from flower.utils.search import (And, MatchAll, Or, QuerySyntaxError,
                                 TaskSearchEngine, Term, parse_query)


class TestQueryParser(unittest.TestCase):
    def test_empty_query_matches_all(self):
        self.assertEqual(MatchAll(), parse_query('  '))

    def test_operator_precedence(self):
        self.assertEqual(
            Or((
                Term(None, 'first'),
                And((Term(None, 'second'), Term(None, 'third'))),
            )),
            parse_query('first OR second third')
        )

    def test_parentheses_override_precedence(self):
        self.assertEqual(
            And((
                Or((Term(None, 'first'), Term(None, 'second'))),
                Term(None, 'third'),
            )),
            parse_query('(first OR second) third')
        )

    def test_quoted_phrase_is_one_term(self):
        self.assertEqual(
            Term('args', 'hello world'),
            parse_query('args:"hello world"')
        )

    def test_explicit_and_matches_implicit_and(self):
        self.assertEqual(
            parse_query('first second'),
            parse_query('first AND second'))

    def test_qualifiers_are_case_insensitive(self):
        self.assertEqual(Term('name', 'tasks.fetch'),
                         parse_query('NAME:tasks.fetch'))

    def test_nested_duplicate_terms_are_removed(self):
        self.assertEqual(
            And((Term(None, 'first'), Term(None, 'second'))),
            parse_query('first (first second)')
        )

    def test_invalid_queries_report_the_position(self):
        with self.assertRaisesRegex(
                QuerySyntaxError,
                r'OR must be followed by a search term at position 6\.$'):
            parse_query('first OR')

    def test_invalid_queries(self):
        invalid_queries = {
            'ab': 'at least 3 characters',
            'name:': 'requires a value',
            'first AND': 'AND must be followed',
            'NOT first': 'NOT is not supported',
            '-first': "Negation with '-' is not supported",
            '()': 'Empty group',
            '(first': 'Missing closing parenthesis',
            '"first': 'Unterminated quoted phrase',
        }

        for query, message in invalid_queries.items():
            with self.subTest(query=query):
                with self.assertRaisesRegex(QuerySyntaxError, message):
                    parse_query(query)

    def test_query_size_and_nesting_limits(self):
        with self.assertRaisesRegex(QuerySyntaxError, 'exceeds 2048 characters'):
            parse_query('a' * 2049)
        with self.assertRaisesRegex(QuerySyntaxError, 'exceeds 5 levels'):
            parse_query('(' * 6 + 'first' + ')' * 6)

    def test_token_limit_counts_parentheses(self):
        with self.assertRaisesRegex(QuerySyntaxError, 'exceeds 128 tokens'):
            parse_query('(first) ' * 43)

    def test_state_qualifier_requires_colon(self):
        self.assertEqual(Term('state', 'STARTED'), parse_query('state:STARTED'))
        self.assertEqual(Term(None, 'stateSTARTED'), parse_query('stateSTARTED'))


class TestTaskSearchEngine(unittest.TestCase):
    @staticmethod
    def create_task(uuid, name, state, worker, *, args=None, kwargs=None,
                    result=None, timestamp=0):
        return SimpleNamespace(
            uuid=uuid,
            name=name,
            state=state,
            worker=SimpleNamespace(hostname=worker) if worker else None,
            args=[] if args is None else args,
            kwargs={} if kwargs is None else kwargs,
            result=result,
            timestamp=timestamp,
        )

    def setUp(self):
        self.tasks = {
            '1': self.create_task(
                '1', 'tasks.fetch', 'FAILURE', 'worker-a',
                args=['customer-123'], kwargs={'priority': 'high'},
                result='connection timeout', timestamp=1),
            '2': self.create_task(
                '2', 'tasks.store', 'SUCCESS', 'worker-b',
                args=['customer-456'], kwargs={'priority': 'low'},
                result='stored', timestamp=2),
            '3': self.create_task(
                '3', 'tasks.fetch', 'RETRY', 'worker-a',
                args=['customer-789'], kwargs="{'priority': 'high'}",
                result='retry timeout', timestamp=3),
            '4': self.create_task(
                '4', 'tasks.report', 'SUCCESS', None,
                args=['hello world'], kwargs={'label': 'some value'},
                result=None, timestamp=4),
        }
        self.engine = TaskSearchEngine()
        self.engine.rebuild(self.tasks.items())

    def test_mixed_boolean_query(self):
        self.assertEqual(
            {'1', '3'},
            self.engine.matching_ids(
                '(state:FAILURE OR state:RETRY) result:timeout')
        )

    def test_exact_kwargs_query_supports_native_and_string_dicts(self):
        self.assertEqual(
            {'1', '3'},
            self.engine.matching_ids('kwargs:priority=HIGH')
        )

    def test_quoted_args_and_kwargs(self):
        self.assertEqual({'4'}, self.engine.matching_ids('args:"hello world"'))
        self.assertEqual(
            {'4'}, self.engine.matching_ids('kwargs:label="some value"'))

    def test_missing_result_does_not_create_a_false_match(self):
        self.assertEqual(
            {'1', '3'}, self.engine.matching_ids('result:timeout'))

    def test_qualified_searches_are_case_insensitive(self):
        expected_results = {
            'name:FETCH': {'1', '3'},
            'worker:WORKER-A': {'1', '3'},
            'args:CUSTOMER': {'1', '2', '3'},
            'kwargs:PRIORITY': {'1', '2', '3'},
            'result:TIMEOUT': {'1', '3'},
        }

        for query, expected in expected_results.items():
            with self.subTest(query=query):
                self.assertEqual(expected, self.engine.matching_ids(query))

    def test_state_search_is_exact(self):
        self.assertEqual(set(), self.engine.matching_ids('state:FAIL'))
        self.assertEqual({'1'}, self.engine.matching_ids('state:failure'))

    def test_unqualified_search_includes_uuid(self):
        task = self.create_task(
            'unique-uuid-123', 'job.execute', 'SUCCESS', 'worker-a')
        self.engine.upsert(task)

        self.assertEqual(
            {'unique-uuid-123'}, self.engine.matching_ids('uuid-123'))

    def test_candidate_set_limits_all_or_branches(self):
        self.assertEqual(
            {'1'},
            self.engine.matching_ids(
                'state:SUCCESS OR state:FAILURE', candidates={'1'}))

    def test_upsert_replaces_stale_document_and_postings(self):
        task = self.tasks['1']
        task.state = 'SUCCESS'
        task.result = 'completed'

        self.engine.upsert(task)

        self.assertEqual(set(), self.engine.matching_ids('state:FAILURE'))
        self.assertEqual({'3'}, self.engine.matching_ids('result:timeout'))
        self.assertEqual({'1', '2', '4'},
                         self.engine.matching_ids('state:SUCCESS'))
        self.assertEqual({'1'}, self.engine.matching_ids('result:completed'))

    def test_filters_sorting_counts_and_pagination(self):
        page = self.engine.search(
            self.tasks,
            'name:tasks',
            worker='worker-a',
            sort_by='timestamp',
            descending=True,
            offset=1,
            limit=1,
        )

        self.assertEqual(['1'], page.task_ids)
        self.assertEqual(2, page.filtered_count)
        self.assertEqual(4, page.total_count)

    def test_remove_clears_document_and_postings(self):
        self.engine.remove('1')

        self.assertNotIn('1', self.engine.documents)
        self.assertEqual(set(), self.engine.matching_ids('state:FAILURE'))
        self.assertEqual({'3'},
                         self.engine.matching_ids('kwargs:priority=high'))
        self.assertEqual({'3'}, self.engine.matching_ids('result:timeout'))

    def test_rebuild_removes_stale_documents_and_postings(self):
        self.engine.rebuild([('4', self.tasks['4'])])

        self.assertEqual({'4'}, set(self.engine.documents))
        self.assertEqual(set(), self.engine.matching_ids('state:FAILURE'))
        self.assertEqual({'4'}, self.engine.matching_ids('state:SUCCESS'))

    def test_exact_filters_and_time_ranges(self):
        self.tasks['1'].received = 10
        self.tasks['1'].started = 20
        self.tasks['3'].received = 30
        self.tasks['3'].started = 40

        page = self.engine.search(
            self.tasks,
            task_type='tasks.fetch',
            worker='worker-a',
            received_start=20,
            started_end=40,
        )

        self.assertEqual(['3'], page.task_ids)
        self.assertEqual(1, page.filtered_count)
        self.assertEqual(4, page.total_count)

    def test_default_sort_and_page_limit(self):
        page = self.engine.search(self.tasks, limit=2)

        self.assertEqual(['4', '3'], page.task_ids)
        self.assertEqual(4, page.filtered_count)
        self.assertEqual(4, page.total_count)

    def test_queries_return_expected_tasks(self):
        expected_results = {
            'customer': {'1', '2', '3'},
            'name:fetch': {'1', '3'},
            'state:FAILURE': {'1'},
            'kwargs:priority=high': {'1', '3'},
            'customer result:timeout': {'1', '3'},
            '(state:FAILURE OR state:RETRY) result:timeout': {'1', '3'},
        }

        for query, expected in expected_results.items():
            with self.subTest(query=query):
                self.assertEqual(expected, self.engine.matching_ids(query))


class TestSearchIndexLifecycle(unittest.TestCase):
    @staticmethod
    def received_event(uuid, name, clock):
        return Event(
            'task-received', uuid=uuid, name=name, args=[], kwargs={},
            retries=0, eta=None, hostname='worker1', clock=clock,
            local_received=time.time())

    def test_events_update_documents_and_remove_evicted_tasks(self):
        state = EventsState(max_tasks_in_memory=2)
        state.event(self.received_event('1', 'tasks.first', 1))
        state.event(Event(
            'task-failed', uuid='1', hostname='worker1', clock=2,
            local_received=time.time(), exception='timeout', traceback='trace'))

        self.assertEqual({'1'}, state.search_engine.matching_ids('state:FAILURE'))

        state.event(self.received_event('2', 'tasks.second', 3))
        state.event(self.received_event('3', 'tasks.third', 4))

        self.assertEqual({'2', '3'}, set(state.tasks))
        self.assertEqual({'2', '3'}, set(state.search_engine.documents))
        self.assertEqual(set(),
                         state.search_engine.matching_ids('state:FAILURE'))

    def test_event_removes_the_actual_least_recently_used_task(self):
        state = EventsState(max_tasks_in_memory=2)
        state.event(self.received_event('1', 'tasks.first', 1))
        state.event(self.received_event('2', 'tasks.second', 2))

        state.tasks['1']  # Mark task 1 as more recently used than task 2.
        state.event(self.received_event('3', 'tasks.third', 3))

        self.assertEqual({'1', '3'}, set(state.tasks))
        self.assertEqual({'1', '3'}, set(state.search_engine.documents))
        self.assertEqual(set(), state.search_engine.matching_ids('name:second'))
        self.assertEqual({'1'}, state.search_engine.matching_ids('name:first'))
        self.assertEqual({'3'}, state.search_engine.matching_ids('name:third'))

    def test_persisted_state_rebuilds_the_index(self):
        state = EventsState()
        state.event(self.received_event('1', 'tasks.first', 1))

        restored = pickle.loads(pickle.dumps(state))

        self.assertEqual({'1'}, restored.search_engine.matching_ids('name:first'))

    def test_clearing_tasks_rebuilds_the_index(self):
        state = EventsState()
        state.event(self.received_event('1', 'tasks.finished', 1))
        state.event(Event(
            'task-succeeded', uuid='1', hostname='worker1', clock=2,
            local_received=time.time(), result='done', runtime=0))
        state.event(self.received_event('2', 'tasks.active', 3))

        state._clear_tasks()

        self.assertEqual({'2'}, set(state.tasks))
        self.assertEqual({'2'}, set(state.search_engine.documents))
        self.assertEqual(set(),
                         state.search_engine.matching_ids('name:finished'))
        self.assertEqual({'2'},
                         state.search_engine.matching_ids('name:active'))


if __name__ == '__main__':
    unittest.main()
