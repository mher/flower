from __future__ import absolute_import

from tornado import web

from ..views import BaseHandler
from ..models import TaskModel, WorkersModel


class TaskView(BaseHandler):
    def get(self, task_id):
        task = TaskModel.get_task_by_id(self.application, task_id)
        if task is None:
            raise web.HTTPError(404, "Unknown task '%s'" % task_id)

        self.render("task.html", task=task)


class TasksView(BaseHandler):
    def get(self):
        app = self.application
        limit = self.get_argument('limit', None)
        worker = self.get_argument('worker', None)
        type = self.get_argument('type', None)

        limit = limit and int(limit)
        worker = worker if worker != 'All' else None
        type = type if type != 'All' else None

        tasks = TaskModel.iter_tasks(app, limit=limit, type=type, worker=worker)
        workers = WorkersModel.get_workers(app)
        seen_task_types = TaskModel.seen_task_types(app)

        self.render("tasks.html", tasks=tasks,
                                  task_types=seen_task_types,
                                  workers=workers,
                                  limit=limit,
                                  worker=worker,
                                  type=type)
