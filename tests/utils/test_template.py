import unittest

from flower.utils.template import humanize, format_time


class TestHumanize(unittest.TestCase):
    def test_None(self):
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
        from pytz import utc
        self.assertEqual(1343911558.305793, humanize(1343911558.305793))
        self.assertEqual(format_time(1343911558.305793, utc),
                         humanize(1343911558.305793, type='time'))

    def test_strings(self):
        self.assertEqual('Max tasks per child',
                         humanize('max_tasks_per_child'))
        self.assertEqual('URI prefix', humanize('uri_prefix'))
        self.assertEqual('Max concurrency', humanize('max-concurrency'))


if __name__ == '__main__':
    unittest.main()
