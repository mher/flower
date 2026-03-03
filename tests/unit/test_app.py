import time
import unittest

import celery
from tornado.ioloop import IOLoop
from tornado.options import options

from flower import command  # noqa: F401 side effect - define options
from flower.app import Flower
from flower.events import Events
from flower.urls import handlers, settings


class TestQueueCache(unittest.TestCase):
    def setUp(self):
        capp = celery.Celery()
        events = Events(capp, IOLoop.current())
        self.app = Flower(capp=capp, events=events,
                          options=options, handlers=handlers, **settings)
        self.app._queue_cache_ttl = 5.0

    def test_cache_miss_returns_none(self):
        result = self.app.get_cached_queue_stats(frozenset(['q1', 'q2']))
        self.assertIsNone(result)

    def test_cache_hit_returns_copy(self):
        names_key = frozenset(['q1', 'q2'])
        data = [{'name': 'q1', 'messages': 5}, {'name': 'q2', 'messages': 10}]
        self.app.set_queue_cache(names_key, data)

        result = self.app.get_cached_queue_stats(names_key)
        self.assertEqual(result, data)
        self.assertIsNot(result, data)

    def test_cache_returns_deep_copy_to_prevent_mutation(self):
        """Mutating dict elements in the returned list must not affect the cache."""
        names_key = frozenset(['q1'])
        data = [{'name': 'q1', 'messages': 5}]
        self.app.set_queue_cache(names_key, data)

        result = self.app.get_cached_queue_stats(names_key)
        result[0]['messages'] = 999

        result2 = self.app.get_cached_queue_stats(names_key)
        self.assertEqual(result2[0]['messages'], 5)

    def test_cache_expires_after_ttl(self):
        names_key = frozenset(['q1'])
        data = [{'name': 'q1', 'messages': 5}]
        self.app.set_queue_cache(names_key, data)

        ts, key, result = self.app._queue_cache
        self.app._queue_cache = (ts - 10.0, key, result)

        self.assertIsNone(self.app.get_cached_queue_stats(names_key))

    def test_cache_miss_on_different_names(self):
        names_key = frozenset(['q1'])
        data = [{'name': 'q1', 'messages': 5}]
        self.app.set_queue_cache(names_key, data)

        different_key = frozenset(['q1', 'q2'])
        self.assertIsNone(self.app.get_cached_queue_stats(different_key))

    def test_cache_disabled_when_ttl_zero(self):
        self.app._queue_cache_ttl = 0
        names_key = frozenset(['q1'])
        data = [{'name': 'q1', 'messages': 5}]
        self.app.set_queue_cache(names_key, data)

        self.assertIsNone(self.app.get_cached_queue_stats(names_key))


if __name__ == '__main__':
    unittest.main()
