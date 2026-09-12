import time
import unittest

from pytz import utc

from flower.utils.template import format_duration, format_time, format_value, humanize, task_link


class TestHumanize(unittest.TestCase):
    def test_none(self):
        self.assertEqual('', humanize(None))

    def test_bool(self):
        self.assertEqual(True, humanize(True))
        self.assertEqual(False, humanize(False))

    def test_numbers(self):
        self.assertEqual(0, humanize(0))
        self.assertEqual(3, humanize(3))
        self.assertEqual(0.2, humanize(0.2))

    def test_keywords(self):
        self.assertEqual('SSL', humanize('ssl'))
        self.assertEqual('SSL', humanize('SSL'))

        self.assertEqual('URI', humanize('uri'))
        self.assertEqual('URI', humanize('URI'))

        self.assertEqual('UUID', humanize('uuid'))
        self.assertEqual('UUID', humanize('UUID'))

        self.assertEqual('ETA', humanize('eta'))
        self.assertEqual('ETA', humanize('ETA'))

        self.assertEqual('URL', humanize('url'))
        self.assertEqual('URL', humanize('URL'))

        self.assertEqual('args', humanize('args'))
        self.assertEqual('kwargs', humanize('kwargs'))

    def test_uuid(self):
        uuid = '5cf83762-9507-4dc5-8e5a-ad730379b099'
        self.assertEqual(uuid, humanize(uuid))

    def test_sequences(self):
        self.assertEqual('2, 3', humanize([2, 3]))
        self.assertEqual('2, foo, 1.2', humanize([2, 'foo', 1.2]))
        self.assertEqual([None, None], humanize([None, None]))
        self.assertEqual([4, {1: 1}], humanize([4, {1: 1}]))

    def test_time(self):
        self.assertEqual(1343911558.305793, humanize(1343911558.305793))
        self.assertEqual(format_time(1343911558.305793, utc),
                         humanize(1343911558.305793, type='time'))

    def test_natural_time(self):
        self.assertEqual(humanize(time.time()-1, type='natural-time-utc'),
                         'a second ago')
        self.assertEqual(humanize(time.time()-1, type='natural-time'),
                         'a second ago')

    def test_strings(self):
        self.assertEqual('Max tasks per child',
                         humanize('max_tasks_per_child'))
        self.assertEqual('URI prefix', humanize('uri_prefix'))
        self.assertEqual('Max concurrency', humanize('max-concurrency'))


class TestFormatDuration(unittest.TestCase):
    def test_sub_millisecond(self):
        self.assertEqual('0.87 ms', format_duration(0.000869922005222179))

    def test_milliseconds(self):
        self.assertEqual('123.46 ms', format_duration(0.123456))

    def test_seconds(self):
        self.assertEqual('1.50 s', format_duration(1.5))
        self.assertEqual('59.99 s', format_duration(59.99))

    def test_minutes(self):
        self.assertEqual('1m 00s', format_duration(60))
        self.assertEqual('2m 05s', format_duration(125.4))

    def test_hours(self):
        self.assertEqual('1h 02m 03s', format_duration(3723))

    def test_string_input(self):
        self.assertEqual('2.00 s', format_duration('2'))

    def test_humanize_duration(self):
        self.assertEqual('0.87 ms', humanize(0.000869922005222179, type='duration'))

    def test_humanize_duration_zero(self):
        self.assertEqual('0.00 ms', humanize(0, type='duration'))

    def test_humanize_duration_none(self):
        self.assertEqual('', humanize(None, type='duration'))


class TestTaskLink(unittest.TestCase):
    def test_full_and_short_spans(self):
        html = task_link('/task/abc', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890')
        self.assertIn('<span class="task-uuid-full">a1b2c3d4-e5f6-7890-abcd-ef1234567890</span>', html)
        self.assertIn('<span class="task-uuid-short">a1b2c3d4</span>', html)

    def test_link_target_and_title(self):
        html = task_link('/prefix/task/abc', 'abc')
        self.assertTrue(html.startswith('<a href="/prefix/task/abc" title="abc">'))

    def test_escapes_uuid(self):
        html = task_link('/task/x', '<script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)


class TestFormatValue(unittest.TestCase):
    def test_none_is_dash(self):
        self.assertEqual('<span class="value-missing">&mdash;</span>', format_value(None))

    def test_zero_is_kept(self):
        self.assertEqual('0', format_value(0))

    def test_string(self):
        self.assertEqual('redis', format_value('redis'))

    def test_escapes_markup(self):
        self.assertEqual('&lt;b&gt;', format_value('<b>'))
