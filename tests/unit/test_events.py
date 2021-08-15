import time
from unittest.mock import patch, Mock

from celery.events import Event

from flower.events import EventsState
from tests.unit import AsyncHTTPTestCase


class TestGetOnlineWorkers(AsyncHTTPTestCase):
    def test_returns_current_worker_info(self):
        state = EventsState()
        worker = 'worker1'
        tasks_executing = 12
        state.get_or_create_worker(worker)
        events = [
            Event('worker-online', hostname=worker),
            Event('worker-heartbeat', hostname=worker, active=tasks_executing)
        ]

        fake_event_time = time.time()
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = fake_event_time + i
            state.event(e)

        expected_workers_info = {
            worker:
                {
                    'active': tasks_executing,
                    'clock': 1,
                    'freq': 60,
                    'heartbeats': [fake_event_time, fake_event_time + 1],
                    'hostname': worker,
                    'loadavg': None,
                    'pid': None,
                    'processed': None,
                    'status': True,
                    'sw_ident': None,
                    'sw_sys': None,
                    'sw_ver': None,
                    'worker-heartbeat': 1,
                    'worker-online': 1
                }
        }

        self.assertEqual(state.get_online_workers(), expected_workers_info)

    def test_removes_info_for_offline_workers_if_purging_is_enabled(self):
        state = EventsState()
        worker_offline = 'worker1'
        worker_online = 'worker2'
        tasks_executing = 12
        state.get_or_create_worker(worker_offline)
        events = [
            Event('worker-online', hostname=worker_offline),
            Event('worker-heartbeat', hostname=worker_offline, active=tasks_executing),
            Event('worker-offline', hostname=worker_offline),
            Event('worker-online', hostname=worker_online),
        ]

        fake_event_time = time.time()
        for i, e in enumerate(events):
            e['clock'] = i
            e['local_received'] = fake_event_time + i
            state.event(e)

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = 0
            workers_info = state.get_online_workers()

        expected_workers_info = {
            worker_online:
                {
                    'active': None,
                    'clock': 3,
                    'freq': 60,
                    'heartbeats': [fake_event_time + 3],
                    'hostname': worker_online,
                    'loadavg': None,
                    'pid': None,
                    'processed': None,
                    'status': True,
                    'sw_ident': None,
                    'sw_sys': None,
                    'sw_ver': None,
                    'worker-online': 1
                }
        }

        self.assertEqual(workers_info, expected_workers_info)


class TestGetOfflineWorkers(AsyncHTTPTestCase):
    def test_returns_empty_set_if_all_workers_are_online(self):
        state = EventsState()
        workers = {
            'worker1': {
                'status': True,
            },
            'worker2': {
                'status': True
            }
        }

        self.assertEqual(state.get_offline_workers(workers=workers), set())

    def test_returns_offline_worker_missing_heartbeats(self):
        state = EventsState()
        worker = 'worker1'
        workers = {
            worker: {
                'status': False,
                'heartbeats': []
            },
        }

        self.assertEqual(state.get_offline_workers(workers=workers), {worker})

    @patch('flower.events.time.time')
    def test_does_not_return_worker_as_offline_if_last_heartbeat_within_purge_offline_workers_option(self, mock_time):
        fake_timestamp = 100
        purge_offline_workers = 10
        mock_time.return_value = fake_timestamp

        state = EventsState()
        worker = 'worker1'
        workers = {
            worker: {
                'status': False,
                'heartbeats': [fake_timestamp - purge_offline_workers - 2, fake_timestamp - purge_offline_workers]
            },
        }

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = purge_offline_workers
            self.assertEqual(state.get_offline_workers(workers=workers), set())

    @patch('flower.events.time.time')
    def test_returns_offline_worker_if_last_heartbeat_too_old(self, mock_time):
        fake_timestamp = 100
        purge_offline_workers = 10
        mock_time.return_value = fake_timestamp

        state = EventsState()
        worker = 'worker1'
        workers = {
            worker: {
                'status': False,
                'heartbeats': [fake_timestamp - purge_offline_workers - 2, fake_timestamp - purge_offline_workers - 1]
            },
        }

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = purge_offline_workers
            self.assertEqual(state.get_offline_workers(workers=workers), {worker})


class TestRemoveMetricsForOfflineWorkers(AsyncHTTPTestCase):
    def test_does_not_remove_metrics_if_purge_offline_workers_is_none(self):
        state = EventsState()
        mock_remove_metrics_for_offline_workers = Mock()
        state.metrics.remove_metrics_for_offline_workers = mock_remove_metrics_for_offline_workers

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = None
            state.remove_metrics_for_offline_workers()

        mock_remove_metrics_for_offline_workers.assert_not_called()

    def test_does_not_remove_metrics_if_there_are_no_offline_workers(self):
        state = EventsState()
        mock_remove_metrics_for_offline_workers = Mock()
        state.metrics.remove_metrics_for_offline_workers = mock_remove_metrics_for_offline_workers

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = 0
            state.remove_metrics_for_offline_workers()

        mock_remove_metrics_for_offline_workers.assert_not_called()

    def test_removes_metrics_for_offline_workers_only(self):
        state = EventsState()
        worker_offline = 'worker1'
        worker_online = 'worker2'
        state.get_or_create_worker(worker_offline)
        state.get_or_create_worker(worker_online)
        events = [
            Event('worker-online', hostname=worker_offline),
            Event('worker-heartbeat', hostname=worker_offline, active=1),
            Event('worker-offline', hostname=worker_offline),
            Event('worker-online', hostname=worker_online),
        ]

        for i, e in enumerate(events):
            e['clock'] = i
            import time
            e['local_received'] = time.time()
            state.event(e)

        mock_remove_metrics_for_offline_workers = Mock()
        state.metrics.remove_metrics_for_offline_workers = mock_remove_metrics_for_offline_workers

        with patch('flower.events.options') as mock_options:
            mock_options.purge_offline_workers = 0
            state.remove_metrics_for_offline_workers()

        mock_remove_metrics_for_offline_workers.assert_called_once_with(offline_workers={worker_offline})
