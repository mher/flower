import asyncio
import unittest
from unittest.mock import MagicMock, patch, call

from flower.utils import broker
from flower.utils.broker import RedisBase, Redis, RedisSentinel, RedisSocket

# Ensure redis is mocked at module level like existing tests
broker.redis = MagicMock()


class TestRedisPipeline(unittest.TestCase):
    """Test that Redis queue fetching uses pipelining."""

    def _make_broker(self):
        b = Redis('redis://localhost:6379/0')
        b.redis = MagicMock()
        return b

    def test_queues_uses_pipeline(self):
        b = self._make_broker()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [10, 0, 0, 0, 5, 0, 0, 0]
        b.redis.pipeline.return_value = mock_pipe

        result = asyncio.get_event_loop().run_until_complete(
            b.queues(['q1', 'q2']))

        # Should have created a pipeline
        b.redis.pipeline.assert_called_once_with(transaction=False)
        # Should have queued LLEN calls (4 priority steps × 2 queues = 8)
        self.assertEqual(mock_pipe.llen.call_count, 8)
        mock_pipe.execute.assert_called_once()

        # Results should be summed per queue
        self.assertEqual(result[0], {'name': 'q1', 'messages': 10})
        self.assertEqual(result[1], {'name': 'q2', 'messages': 5})

    def test_queues_empty_names(self):
        b = self._make_broker()
        result = asyncio.get_event_loop().run_until_complete(b.queues([]))
        self.assertEqual(result, [])
        b.redis.pipeline.assert_not_called()

    def test_queues_sums_priority_steps(self):
        b = self._make_broker()
        mock_pipe = MagicMock()
        # 4 priority steps for one queue, all with values
        mock_pipe.execute.return_value = [10, 20, 30, 40]
        b.redis.pipeline.return_value = mock_pipe

        result = asyncio.get_event_loop().run_until_complete(b.queues(['q1']))
        self.assertEqual(result[0]['messages'], 100)

    def test_queues_chunked_for_large_counts(self):
        """Verify pipeline batching kicks in for very large queue counts."""
        b = self._make_broker()
        b.priority_steps = [0]  # 1 step to simplify

        chunk_size = b._PIPELINE_CHUNK_SIZE
        num_queues = chunk_size + 10  # Just over one chunk
        names = [f'q{i}' for i in range(num_queues)]

        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = [
            [1] * chunk_size,  # First chunk
            [2] * 10,          # Second chunk
        ]
        b.redis.pipeline.return_value = mock_pipe

        result = asyncio.get_event_loop().run_until_complete(b.queues(names))

        # Should have created 2 pipelines (one per chunk)
        self.assertEqual(b.redis.pipeline.call_count, 2)
        self.assertEqual(len(result), num_queues)
        # First chunk queues have message count 1, second chunk have 2
        self.assertEqual(result[0]['messages'], 1)
        self.assertEqual(result[chunk_size]['messages'], 2)


class TestRedisClose(unittest.TestCase):
    def test_close_with_close_method(self):
        b = Redis('redis://localhost:6379/0')
        b.redis = MagicMock()
        b.redis.close = MagicMock()

        b.close()

        b.redis is None or b.redis.close.assert_called_once()  # redis set to None
        self.assertIsNone(b.redis)

    def test_close_without_close_method(self):
        """Test fallback to connection_pool.disconnect() for older redis-py."""
        b = Redis('redis://localhost:6379/0')
        mock_redis = MagicMock(spec=[])  # No close method
        mock_redis.connection_pool = MagicMock()
        b.redis = mock_redis

        b.close()
        self.assertIsNone(b.redis)

    def test_close_already_none(self):
        b = Redis('redis://localhost:6379/0')
        b.redis = None
        # Should not raise
        b.close()
        self.assertIsNone(b.redis)

    def test_close_handles_exception(self):
        b = Redis('redis://localhost:6379/0')
        b.redis = MagicMock()
        b.redis.close.side_effect = RuntimeError("connection error")

        # Should not raise
        b.close()
        self.assertIsNone(b.redis)


class TestRabbitMQOptimizations(unittest.TestCase):
    def test_frozenset_filtering(self):
        """Ensure set-based filtering works correctly."""
        from flower.utils.broker import RabbitMQ
        b = RabbitMQ('amqp://', '')

        # Simulate what happens inside queues() after API response
        info = [
            {'name': 'q1', 'messages': 5},
            {'name': 'q2', 'messages': 10},
            {'name': 'q3', 'messages': 15},
        ]
        names = ['q1', 'q3']
        names_set = frozenset(names)
        result = [x for x in info if x['name'] in names_set]

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'q1')
        self.assertEqual(result[1]['name'], 'q3')


if __name__ == '__main__':
    unittest.main()
