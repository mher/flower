from __future__ import absolute_import

import copy
import logging

try:
    from itertools import imap
except ImportError:
    imap = map

import celery

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


class TasksView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp
        limit = self.get_argument('limit', default=None, type=int)
        worker = self.get_argument('worker', None)
        type = self.get_argument('type', None)
        state = self.get_argument('state', None)
        sort_by = self.get_argument('sort', None)
        received_start = self.get_argument('received-start', None)
        received_end = self.get_argument('received-end', None)
        started_start = self.get_argument('started-start', None)
        started_end = self.get_argument('started-end', None)
        search = self.get_argument('search', None)

        worker = worker if worker != 'All' else None
        type = type if type != 'All' else None
        state = state if state != 'All' else None

        tasks = iter_tasks(
            app.events,
            limit=limit,
            type=type,
            worker=worker,
            state=state,
            sort_by=sort_by,
            received_start=received_start,
            received_end=received_end,
            started_start=started_start,
            started_end=started_end,
            search=search,
        )
        tasks = imap(self.format_task, tasks)
        workers = app.events.state.workers
        seen_task_types = app.events.state.task_types()
        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.CELERY_TIMEZONE:
            time += '-' + capp.conf.CELERY_TIMEZONE
        params = dict((k, v[-1]) for (k, v) in self.request.query_arguments.items())

        columns = app.options.tasks_columns.split(',')
        self.render(
            "tasks.html",
            tasks=tasks,
            columns=columns,
            task_types=seen_task_types,
            all_states=celery.states.ALL_STATES,
            workers=workers,
            limit=limit,
            worker=worker,
            type=type,
            state=state,
            sort_by=sort_by,
            received_start=received_start,
            received_end=received_end,
            started_start=started_start,
            started_end=started_end,
            params=params,
            time=time,
            search=search
        )

    def format_task(self, args):
        uuid, task = args
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            task = custom_format_task(copy.copy(task))
        return uuid, task


class TasksDataTable(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        draw = self.get_argument('draw', type=int)
        start = self.get_argument('start', type=int)
        length = self.get_argument('length', type=int)
        search = self.get_argument('search[value]', type=str)

        column= self.get_argument('order[0][column]', type=int)
        sort_by = self.get_argument('columns[%s][data]' % column, type=str)
        sort_order = self.get_argument('order[0][dir]', type=str) == 'asc'

        tasks = sorted(iter_tasks(app.events, search=search),
                       key=lambda x: getattr(x[1], sort_by),
                       reverse=sort_order)
        filtered_tasks = []
        i = 0
        for _, task in tasks:
            if i < start:
                i += 1
                continue
            if i >= (start + length):
                break
            task = as_dict(task)
            task['worker'] = task['worker'].hostname
            filtered_tasks.append(task)
            i += 1

        self.write(dict(draw=draw, data=filtered_tasks,
                        recordsTotal=len(tasks),
                        recordsFiltered=len(tasks)))

    def format_task(self, args):
        uuid, task = args
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            task = custom_format_task(copy.copy(task))
        return uuid, task

    def attr_sort(self, lst, attr):
        key = lambda x: getattr(x, attr)
        return sorted(lst, key=lambda x: getattr(x, attr))
