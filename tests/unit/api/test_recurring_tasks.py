import json
from unittest.mock import Mock

from tests.unit.api import BaseApiTestCase


class TestRecurringTasksApi(BaseApiTestCase):
    def test_get_recurring_tasks_empty(self):
        r = self.get('/api/recurring-tasks')
        self.assertEqual(200, r.code)
        data = json.loads(r.body)
        self.assertIn('recurring_tasks', data)
        self.assertEqual([], data['recurring_tasks'])

    def test_get_recurring_tasks_populated(self):
        self._app.capp.conf.beat_schedule = {
            'heartbeat': {
                'task': 'tasks.heartbeat',
                'schedule': 10.0,
                'args': ['ping'],
                'kwargs': {'timeout': 5},
                'options': {'queue': 'beats'}
            }
        }

        r = self.get('/api/recurring-tasks')
        self.assertEqual(200, r.code)
        data = json.loads(r.body)
        self.assertEqual(1, len(data['recurring_tasks']))
        s = data['recurring_tasks'][0]
        self.assertEqual('heartbeat', s['name'])
        self.assertEqual('tasks.heartbeat', s['task'])
        self.assertEqual('every 10s', s['schedule'])
        self.assertEqual(['ping'], s['args'])
        self.assertEqual({'timeout': 5}, s['kwargs'])
        self.assertEqual({'queue': 'beats'}, s['options'])
