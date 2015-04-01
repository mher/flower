import unittest
from collections import namedtuple

from flower.utils.search import parse_search_terms, stringified_dict_contains_value, satisfies_search_terms


class TestSearchParser(unittest.TestCase):
    def test_any_value(self):
        self.assertEqual(
            {'any': 'someval'},
            parse_search_terms('someval')
        )

    def test_result_value(self):
        self.assertEqual(
            {'result': 'resval'},
            parse_search_terms('result=resval')
        )

    def test_kwargs(self):
        self.assertEqual(
            {'kwargs': {'some_kwarg': 'some_value'}},
            parse_search_terms('some_kwarg=some_value')
        )
        self.assertEqual(
            {'kwargs': {'some_kwarg1': 'some_value1', 'some_kwarg2': 'some_value2'}},
            parse_search_terms('some_kwarg1=some_value1,some_kwarg2=some_value2')
        )

    def test_strip_spaces(self):
        self.assertEqual(
            {'any': 'someval'},
            parse_search_terms('    someval  ')
        )
        self.assertEqual(
            {'kwargs': {'some_kwarg': 'some_value'}},
            parse_search_terms('     some_kwarg=some_value   ')
        )


class TestStringfiedDictChecker(unittest.TestCase):
    def test_stringifies_args(self):
        self.assertEqual(
            True,
            stringified_dict_contains_value('test', 5, "{'test': 5}")
        )

    def test_works_for_nonexisting_kwargs(self):
        self.assertEqual(
            False,
            stringified_dict_contains_value('non_exisiting_kwarg', '5', "{'test': 5}")
        )

    def test_works_for_kwargs_in_different_parts_of_string(self):
        for key, value in [('key1', '1'), ('key2', '2'), ('key3', '3')]:
            self.assertEqual(
                True,
                stringified_dict_contains_value(key, value, "{'key1': 1, 'key2': 2, 'key3': 3}")
            )


class TestTaskFiltering(unittest.TestCase):
    def _create_task(self, result=None, args=None, kwargs='{}'):
        args = args or []
        TaskMockClass = namedtuple('Task', 'result args kwargs')
        return TaskMockClass(result, args, kwargs)

    def setUp(self):
        self.task = self._create_task(kwargs="{'kwarg1': 1, 'kwarg2': 22}")

    def test_kwarg_search_works(self):
        self.assertEqual(
            True,
            satisfies_search_terms(self.task, None, None, {'kwarg1': 1})
        )
        self.assertEqual(
            False,
            satisfies_search_terms(self.task, None, None, {'kwarg1': 2})
        )


if __name__ == '__main__':
    unittest.main()
