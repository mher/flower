import copy
import logging

from tornado import web

from ..utils.search import QuerySyntaxError
from ..utils.tasks import as_dict, get_task_by_id, search_tasks
from ..views import BaseHandler

logger = logging.getLogger(__name__)


class TaskView(BaseHandler):
    @web.authenticated
    def get(self, task_id):
        task = get_task_by_id(self.application.events, task_id)

        if task is None:
            raise web.HTTPError(404, f"Unknown task '{task_id}'")
        task = self.format_task(task)
        self.render(
            "task.html",
            task=task,
            read_only=self.application.options.read_only,
        )


class TasksDataTable(BaseHandler):
    @web.authenticated
    # pylint: disable=too-many-locals
    def get(self):
        app = self.application
        draw = self.get_argument('draw', type=int)
        start = self.get_argument('start', type=int)
        length = self.get_argument('length', type=int)
        search = self.get_argument('search[value]', type=str)

        column = self.get_argument('order[0][column]', type=int)
        sort_by = self.get_argument(f'columns[{column}][data]', type=str)
        sort_order = self.get_argument('order[0][dir]', type=str) == 'desc'

        try:
            page = search_tasks(
                app.events,
                search=search,
                sort_by=sort_by,
                descending=sort_order,
                offset=start,
                limit=length)
        except QuerySyntaxError as exc:
            self.write(dict(
                draw=draw,
                data=[],
                recordsTotal=len(app.events.state.tasks),
                recordsFiltered=0,
                searchError=str(exc)))
            return

        filtered_tasks = []
        task_map = getattr(app.events.state.tasks, 'data', app.events.state.tasks)

        for task_id in page.task_ids:
            task = task_map.get(task_id)
            if task is None:
                continue
            task_dict = as_dict(self.format_task((task_id, task))[1])
            if task_dict.get('worker'):
                task_dict['worker'] = task_dict['worker'].hostname

            filtered_tasks.append(task_dict)

        self.write(dict(draw=draw, data=filtered_tasks,
                        recordsTotal=page.total_count,
                        recordsFiltered=page.filtered_count))

    @web.authenticated
    def post(self):
        return self.get()

    def format_task(self, task):
        uuid, args = task
        custom_format_task = self.application.options.format_task

        if custom_format_task:
            try:
                args = custom_format_task(copy.copy(args))
            except Exception:
                logger.exception("Failed to format '%s' task", uuid)
        return uuid, args


class TasksView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp

        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.timezone:
            time += '-' + str(capp.conf.timezone)

        self.render(
            "tasks.html",
            tasks=[],
            columns=app.options.tasks_columns,
            time=time,
        )
