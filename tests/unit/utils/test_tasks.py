import datetime
import unittest

from flower.utils.tasks import (MAX_ARG_LENGTH, make_json_serializable,
                                parse_args, parse_kwargs)


class TestParseArgs(unittest.TestCase):
    def test_empty(self):
        self.assertEqual([], parse_args(None))
        self.assertEqual([], parse_args(''))

    def test_json_list(self):
        self.assertEqual([1, 2], parse_args('[1, 2]'))
        self.assertEqual([{'a': [1]}, 'b'], parse_args('[{"a": [1]}, "b"]'))

    def test_python_tuple_repr(self):
        self.assertEqual([1, 2, 3], parse_args('(1, 2, 3)'))
        self.assertEqual(['x'], parse_args("('x',)"))
        self.assertEqual([], parse_args('()'))

    def test_python_list_repr(self):
        self.assertEqual([1, None, True], parse_args('[1, None, True]'))

    def test_truncated_repr_rejected(self):
        with self.assertRaises(ValueError):
            parse_args("(1, 2, 'long-va...")
        with self.assertRaises(ValueError):
            parse_args('...')

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            parse_args('"a string"')
        with self.assertRaises(ValueError):
            parse_args('42')
        with self.assertRaises(ValueError):
            parse_args('{"a": 1}')

    def test_garbage_rejected(self):
        with self.assertRaises(ValueError):
            parse_args('not a literal')

    def test_code_not_executed(self):
        with self.assertRaises(ValueError):
            parse_args('__import__("os").system("true")')

    def test_oversized_input_rejected(self):
        with self.assertRaises(ValueError):
            parse_args('[' + '1,' * MAX_ARG_LENGTH + ']')


class TestParseKwargs(unittest.TestCase):
    def test_empty(self):
        self.assertEqual({}, parse_kwargs(None))
        self.assertEqual({}, parse_kwargs(''))

    def test_json_object(self):
        self.assertEqual({'retry': True, 'n': 3},
                         parse_kwargs('{"retry": true, "n": 3}'))

    def test_python_dict_repr(self):
        self.assertEqual({'count': 5, 'enabled': True},
                         parse_kwargs("{'count': 5, 'enabled': True}"))
        self.assertEqual({}, parse_kwargs('{}'))

    def test_non_dict_rejected(self):
        with self.assertRaises(ValueError):
            parse_kwargs('[1, 2]')
        with self.assertRaises(ValueError):
            parse_kwargs("{'a'}")  # a set literal, not a dict

    def test_garbage_rejected(self):
        with self.assertRaises(ValueError):
            parse_kwargs('invalid json')
        with self.assertRaises(ValueError):
            parse_kwargs("{'a': 1, ...")


class TestMakeJsonSerializable(unittest.TestCase):
    def test_scalars_pass_through(self):
        for value in (None, 'a', 1, 1.5, True):
            self.assertEqual(value, make_json_serializable(value))

    def test_containers_converted(self):
        self.assertEqual([1, 2], make_json_serializable((1, 2)))
        self.assertEqual([1], make_json_serializable({1}))
        self.assertEqual({'a': [1, 2]}, make_json_serializable({'a': (1, 2)}))
        self.assertEqual([[1], {'b': 2}],
                         make_json_serializable([(1,), {'b': 2}]))

    def test_datetime_converted(self):
        dt = datetime.datetime(2026, 7, 9, 12, 0, 0)
        self.assertEqual('2026-07-09T12:00:00', make_json_serializable(dt))
        self.assertEqual('2026-07-09', make_json_serializable(datetime.date(2026, 7, 9)))

    def test_non_serializable_rejected(self):
        with self.assertRaises(TypeError):
            make_json_serializable(b'bytes')
        with self.assertRaises(TypeError):
            make_json_serializable(...)
        with self.assertRaises(TypeError):
            make_json_serializable([1, object()])


if __name__ == '__main__':
    unittest.main()
