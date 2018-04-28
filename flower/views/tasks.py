from __future__ import absolute_import

from functools import total_ordering
import copy
import logging

try:
    from itertools import imap
except ImportError:
    imap = map

from tornado import web

from ..views import BaseHandler
from ..utils.tasks import iter_tasks, get_task_by_id, as_dict

logger = logging.getLogger(__name__)


class TaskView(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        task = get_task_by_id(self.application.events, task_id)

        if task is None:
            raise web.HTTPError(404, "Unknown task '%s'" % task_id)

        self.render("task.html", task=task)


@total_ordering
class Comparable(object):
    """
    Compare two objects, one or more of which may be None.  If one of the
    values is None, the other will be deemed greater.
    """

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def __lt__(self, other):
        try:
            return self.value < other.value
        except TypeError:
            return self.value is None


class TasksDataTable(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        draw = self.get_argument('draw', type=int)
        start = self.get_argument('start', type=int)
        length = self.get_argument('length', type=int)
        search = self.get_argument('search[value]', type=str)

        column = self.get_argument('order[0][column]', type=int)
        sort_by = self.get_argument('columns[%s][data]' % column, type=str)
        sort_order = self.get_argument('order[0][dir]', type=str) == 'desc'

        def key(item):
            return Comparable(getattr(item[1], sort_by))

        sorted_tasks = sorted(
            iter_tasks(app.events, search=search),
            key=key,
            reverse=sort_order
        )

        filtered_tasks = []

        for task in sorted_tasks[start:start + length]:
            task_dict = as_dict(self.format_task(task)[1])
            if task_dict.get('worker'):
                task_dict['worker'] = task_dict['worker'].hostname

            filtered_tasks.append(task_dict)

        self.write(dict(draw=draw, data=filtered_tasks,
                        recordsTotal=len(sorted_tasks),
                        recordsFiltered=len(sorted_tasks)))

    @web.authenticated
    def post(self):
        return self.get()

    def format_task(self, args):
        uuid, task = args
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            try:
                task = custom_format_task(copy.copy(task))
            except:
                logger.exception("Failed to format '%s' task", uuid)
        return uuid, task


class TasksView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp

        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.CELERY_TIMEZONE:
            time += '-' + str(capp.conf.CELERY_TIMEZONE)

        self.render(
            "tasks.html",
            tasks=[],
            columns=app.options.tasks_columns,
            time=time,
        )
