import unittest

from flower.events import get_prometheus_metrics


class TestPrometheusMetricsRemoval(unittest.TestCase):
    """Test remove_worker_metrics using the global singleton to avoid
    duplicate registry errors from prometheus_client."""

    def test_remove_worker_metrics_clears_labels(self):
        metrics = get_prometheus_metrics()
        metrics.worker_online.labels('test_remove_w1').set(1)
        metrics.worker_online.labels('test_remove_w2').set(1)

        self.assertIn(('test_remove_w1',), metrics.worker_online._metrics)

        metrics.remove_worker_metrics('test_remove_w1')

        self.assertNotIn(('test_remove_w1',), metrics.worker_online._metrics)
        self.assertIn(('test_remove_w2',), metrics.worker_online._metrics)

    def test_remove_nonexistent_worker_is_noop(self):
        metrics = get_prometheus_metrics()
        # Should not raise
        metrics.remove_worker_metrics('test_remove_nonexistent_worker_xyz')

    def test_remove_multi_label_metrics(self):
        metrics = get_prometheus_metrics()
        metrics.runtime.labels('test_remove_mw1', 'task1').observe(1.0)
        metrics.runtime.labels('test_remove_mw1', 'task2').observe(2.0)
        metrics.runtime.labels('test_remove_mw2', 'task1').observe(3.0)

        metrics.remove_worker_metrics('test_remove_mw1')

        remaining_keys = list(metrics.runtime._metrics.keys())
        for key in remaining_keys:
            self.assertNotEqual(key[0], 'test_remove_mw1')
        self.assertIn(('test_remove_mw2', 'task1'), metrics.runtime._metrics)

    def test_remove_handles_missing_private_attr(self):
        metrics = get_prometheus_metrics()
        # Temporarily remove _metrics to simulate missing attr
        original = metrics.worker_online._metrics
        try:
            del metrics.worker_online._metrics
            # Should not raise — getattr guard should catch it
            metrics.remove_worker_metrics('w1')
        finally:
            metrics.worker_online._metrics = original


if __name__ == '__main__':
    unittest.main()
