import unittest
from datetime import timedelta
from unittest.mock import Mock

from celery.schedules import crontab, schedule

from flower.utils.recurring_tasks import format_schedule, get_recurring_tasks, get_schedule_type


class TestRecurringTasksUtils(unittest.TestCase):
    def test_get_schedule_type(self):
        self.assertEqual(get_schedule_type(None), 'custom')
        self.assertEqual(get_schedule_type(30), 'interval')
        self.assertEqual(get_schedule_type(timedelta(minutes=5)), 'interval')
        self.assertEqual(get_schedule_type(crontab(minute='*/5')), 'crontab')
        solar_mock = Mock()
        solar_mock.event = 'sunset'
        solar_mock.lat = 37.77
        self.assertEqual(get_schedule_type(solar_mock), 'solar')
    def test_format_schedule_primitives(self):
        self.assertEqual(format_schedule(None), "")
        self.assertEqual(format_schedule(30), "every 30s")
        self.assertEqual(format_schedule(30.5), "every 30.5s")
        self.assertEqual(format_schedule("custom-schedule"), "custom-schedule")

    def test_format_schedule_timedelta(self):
        self.assertEqual(format_schedule(timedelta(seconds=45)), "every 45s")
        self.assertEqual(format_schedule(timedelta(minutes=15)), "every 15m")
        self.assertEqual(format_schedule(timedelta(hours=2, minutes=30)), "every 2h 30m")
        self.assertEqual(format_schedule(timedelta(days=1, hours=2)), "every 1d 2h")

    def test_format_schedule_celery_objects(self):
        cron = crontab(minute='*/15', hour='8-18')
        self.assertIn("*/15 8-18", format_schedule(cron))

        sched = schedule(run_every=timedelta(seconds=10))
        self.assertIn("10", format_schedule(sched))

        # Test solar mock
        solar_mock = Mock()
        solar_mock.event = 'sunset'
        solar_mock.lat = 37.77
        solar_mock.lon = -122.41
        self.assertEqual("solar: sunset (37.77, -122.41)", format_schedule(solar_mock))

    def test_get_recurring_tasks_empty(self):
        capp = Mock()
        capp.conf.beat_schedule = {}
        self.assertEqual(get_recurring_tasks(capp), [])

    def test_get_recurring_tasks_with_entries_and_executions(self):
        capp = Mock()
        capp.conf.beat_schedule = {
            'task-a': {
                'task': 'app.tasks.cleanup',
                'schedule': 60.0,
                'args': [1, 2],
                'kwargs': {'force': True},
                'options': {'queue': 'periodic'}
            },
            'task-b': {
                'task': 'app.tasks.report',
                'schedule': crontab(minute=0, hour=0),
            }
        }

        # Mock events with task state
        events = Mock()
        task_cleanup = Mock()
        task_cleanup.name = 'app.tasks.cleanup'
        task_cleanup.uuid = 'uuid-123'
        task_cleanup.state = 'SUCCESS'
        task_cleanup.received = 1700000000.0
        task_cleanup.timestamp = 1700000000.0
        task_cleanup.started = 1700000000.1
        task_cleanup.succeeded = 1700000001.0
        task_cleanup.failed = None
        task_cleanup.runtime = 0.9
        task_cleanup.result = 'cleaned'

        events.state.tasks = {'uuid-123': task_cleanup}

        recurring_tasks = get_recurring_tasks(capp, events=events)
        self.assertEqual(len(recurring_tasks), 2)

        task_a = next(s for s in recurring_tasks if s['name'] == 'task-a')
        self.assertEqual(task_a['task'], 'app.tasks.cleanup')
        self.assertEqual(task_a['args'], [1, 2])
        self.assertEqual(task_a['kwargs'], {'force': True})
        self.assertEqual(task_a['options'], {'queue': 'periodic'})
        self.assertIsNotNone(task_a['last_execution'])
        self.assertEqual(task_a['last_execution']['uuid'], 'uuid-123')
        self.assertEqual(task_a['last_execution']['state'], 'SUCCESS')

        task_b = next(s for s in recurring_tasks if s['name'] == 'task-b')
        self.assertEqual(task_b['task'], 'app.tasks.report')
        self.assertIsNone(task_b['last_execution'])

    def test_get_latest_task_executions_with_tasks_by_type(self):
        events = Mock()
        task_report = Mock()
        task_report.name = 'app.tasks.report'
        task_report.uuid = 'uuid-report'
        task_report.received = 1700000005.0

        events.state.tasks_by_type = Mock(return_value=[task_report])
        res = get_recurring_tasks(Mock(conf=Mock(beat_schedule={'rep': {'task': 'app.tasks.report', 'schedule': 10}})), events=events)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['last_execution']['uuid'], 'uuid-report')
