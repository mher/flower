from unittest.mock import Mock, call

from flower.api.prometheus_metrics import PrometheusMetrics
from tests.unit import AsyncHTTPTestCase


class TestPrometheusMetrics(AsyncHTTPTestCase):
    def test_remove_metrics_for_offline_workers_removes_label_sets_containing_offline_worker(self):
        prometheus_metrics = PrometheusMetrics()
        worker_online = 'worker_online'
        worker_offline = 'worker_offline'
        event_type = 'task-started'
        task = 'tasks.add'
        other_task = 'tasks.mul'
        worker_online_label_set = (worker_online, event_type, task)
        worker_offline_label_set = (worker_offline, event_type, task)
        other_worker_offline_label_set = (worker_offline, event_type, other_task)

        prometheus_metrics.events.labels(*worker_online_label_set).inc()
        prometheus_metrics.events.labels(*worker_offline_label_set).inc()
        prometheus_metrics.events.labels(*other_worker_offline_label_set).inc()

        offline_workers = {worker_offline}

        mock_remove = Mock()
        prometheus_metrics.events.remove = mock_remove
        prometheus_metrics.remove_metrics_for_offline_workers(offline_workers=offline_workers)

        mock_remove.assert_has_calls(
            [
                call(*worker_offline_label_set),
                call(*other_worker_offline_label_set),
            ],
            any_order=True
        )
