import logging

from tornado import web

from ..utils.recurring_tasks import get_recurring_tasks
from ..views import BaseHandler

logger = logging.getLogger(__name__)


class RecurringTasksView(BaseHandler):
    @web.authenticated
    def get(self):
        capp = self.application.capp
        time = 'natural-time' if self.application.options.natural_time else 'time'
        if capp.conf.timezone:
            time += '-' + str(capp.conf.timezone)

        recurring_tasks = get_recurring_tasks(capp, events=self.application.events)

        self.render(
            "recurring_tasks.html",
            recurring_tasks=recurring_tasks,
            schedules=recurring_tasks,
            time=time,
            read_only=self.application.options.read_only,
            autorefresh=1 if self.application.options.auto_refresh else 0,
        )


class RecurringTaskView(BaseHandler):
    @web.authenticated
    def get(self, task_name):
        capp = self.application.capp
        time = 'natural-time' if self.application.options.natural_time else 'time'
        if capp.conf.timezone:
            time += '-' + str(capp.conf.timezone)

        recurring_tasks = get_recurring_tasks(capp, events=self.application.events)
        recurring_task = next((s for s in recurring_tasks if s['name'] == task_name), None)

        if recurring_task is None:
            raise web.HTTPError(404, f"Unknown recurring task '{task_name}'")

        self.render(
            "recurring_task.html",
            recurring_task=recurring_task,
            schedule=recurring_task,
            time=time,
            read_only=self.application.options.read_only,
        )


