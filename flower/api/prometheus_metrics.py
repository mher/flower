import logging
from typing import List, Tuple, Set

from prometheus_client import Counter as PrometheusCounter, Histogram, Gauge
from prometheus_client.metrics import MetricWrapperBase

logger = logging.getLogger(__name__)


class LabelNames:
    WORKER = 'worker'
    TYPE = 'type'
    TASK = 'task'


class PrometheusMetrics(object):
    events = PrometheusCounter(
        'flower_events_total', "Number of events", [LabelNames.WORKER, LabelNames.TYPE, LabelNames.TASK]
    )
    runtime = Histogram('flower_task_runtime_seconds', "Task runtime", [LabelNames.WORKER, LabelNames.TASK])
    prefetch_time = Gauge(
        'flower_task_prefetch_time_seconds',
        "The time the task spent waiting at the celery worker to be executed.",
        [LabelNames.WORKER, LabelNames.TASK]
    )
    number_of_prefetched_tasks = Gauge(
        'flower_worker_prefetched_tasks',
        'Number of tasks of given type prefetched at a worker',
        [LabelNames.WORKER, LabelNames.TASK]
    )
    worker_online = Gauge('flower_worker_online', "Worker online status", [LabelNames.WORKER])
    worker_number_of_currently_executing_tasks = Gauge(
        'flower_worker_number_of_currently_executing_tasks',
        "Number of tasks currently executing at a worker",
        [LabelNames.WORKER]
    )

    @property
    def transient_metrics(self) -> List[MetricWrapperBase]:
        return [
            self.events,
            self.runtime,
            self.prefetch_time,
            self.number_of_prefetched_tasks,
            self.worker_online,
            self.worker_number_of_currently_executing_tasks
        ]

    def remove_metrics_for_offline_workers(self, offline_workers: Set[str]):
        for metric in self.transient_metrics:
            labels_sets_for_offline_workers = self._get_label_sets_for_offline_workers(
                metric=metric, offline_workers=offline_workers
            )
            for label_set in labels_sets_for_offline_workers:
                try:
                    metric.remove(*label_set)
                    logger.debug('Removed label set: %s for metric %s', label_set, metric)
                except KeyError:
                    pass

    @staticmethod
    def _get_label_sets_for_offline_workers(
            metric: MetricWrapperBase, offline_workers: Set[str]
    ) -> Set[Tuple[str, ...]]:
        sampled_metrics = metric.collect()

        label_sets_for_offline_workers = set()
        for sampled_metric in sampled_metrics:
            for sample in sampled_metric.samples:
                labels = sample.labels
                worker = labels.get(LabelNames.WORKER)
                if worker is None or worker not in offline_workers:
                    continue

                label_sets_for_offline_workers.add(tuple([labels[label_name] for label_name in metric._labelnames]))

        return label_sets_for_offline_workers
