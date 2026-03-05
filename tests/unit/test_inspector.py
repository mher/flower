import unittest
from unittest.mock import MagicMock

from flower.inspector import Inspector


class TestInspectorPurge(unittest.TestCase):
    def test_purge_worker_removes_entry(self):
        inspector = Inspector(MagicMock(), MagicMock(), 1.0)
        inspector.workers['w1'] = {'stats': {}}
        inspector.workers['w2'] = {'stats': {}}

        inspector.purge_worker('w1')

        self.assertNotIn('w1', inspector.workers)
        self.assertIn('w2', inspector.workers)

    def test_purge_worker_noop_for_unknown(self):
        inspector = Inspector(MagicMock(), MagicMock(), 1.0)
        inspector.workers['w1'] = {'stats': {}}

        # Should not raise
        inspector.purge_worker('nonexistent')

        self.assertIn('w1', inspector.workers)

    def test_purge_worker_empty_workers(self):
        inspector = Inspector(MagicMock(), MagicMock(), 1.0)

        # Should not raise on empty defaultdict
        inspector.purge_worker('w1')

        self.assertEqual(len(inspector.workers), 0)


if __name__ == '__main__':
    unittest.main()
