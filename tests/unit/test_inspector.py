import unittest
from unittest.mock import MagicMock

from flower.inspector import Inspector


class TestInspectorPurgeWorker(unittest.TestCase):
    def test_purge_existing_worker(self):
        io_loop = MagicMock()
        capp = MagicMock()
        inspector = Inspector(io_loop, capp, timeout=1.0)

        inspector.workers['w1'] = {'stats': {}, 'timestamp': 1000}
        inspector.workers['w2'] = {'stats': {}, 'timestamp': 1000}

        inspector.purge_worker('w1')

        self.assertNotIn('w1', inspector.workers)
        self.assertIn('w2', inspector.workers)

    def test_purge_nonexistent_worker_is_noop(self):
        io_loop = MagicMock()
        capp = MagicMock()
        inspector = Inspector(io_loop, capp, timeout=1.0)

        # Should not raise
        inspector.purge_worker('nonexistent')
        self.assertEqual(len(inspector.workers), 0)


if __name__ == '__main__':
    unittest.main()
