from __future__ import absolute_import
from __future__ import with_statement

from celery.utils.compat import OrderedDict


class BaseModel(object):
    def __init__(self, app):
        self.app = app

    def __eq__(self, other):
        raise NotImplementedError

    def __ne__(self, other):
        return not self.__eq__(other)


class WorkersModel(BaseModel):
    def __init__(self, app):
        super(WorkersModel, self).__init__(app)
        self.workers = OrderedDict()

        state = self.app.state
        for workername, stat in sorted(state.stats.iteritems()):
            pool = stat.get('pool') or {}
            self.workers[workername] = dict(
                    status=(workername in state.ping),
                    concurrency=pool.get('max-concurrency'),
                    completed_tasks=sum(stat['total'].itervalues()),
                    running_tasks=state.active_tasks.get(workername, []),
                    queues=map(lambda x: x['name'],
                               state.active_queues.get(workername, [])),
                    )

    @classmethod
    def get_latest(cls, app):
        return WorkersModel(app)

    @classmethod
    def get_workers(cls, app):
        return app.state.stats.keys()

    @classmethod
    def is_worker(cls, app, workername):
        return WorkerModel.get_worker(app, workername) is not None

    def __eq__(self, other):
        return other is not None and self.workers == other.workers


class WorkerModel(BaseModel):
    def __init__(self, app, name):
        super(WorkerModel, self).__init__(app)

        state = self.app.state
        self.name = name
        self.stats = state.stats[name]
        self.active_tasks = state.active_tasks.get(name, {})
        self.scheduled_tasks = state.scheduled_tasks.get(name, {})
        self.active_queues = state.active_queues.get(name, {})
        self.revoked_tasks = state.revoked_tasks.get(name, [])
        self.registered_tasks = filter(lambda x: not x.startswith('celery.'),
                                       state.registered_tasks.get(name, {}))
        self.reserved_tasks = state.reserved_tasks.get(name, {})
        self.conf = state.conf.get(name, {})

    @classmethod
    def get_worker(self, app, name):
        if name not in app.state.stats:
            return None
        return WorkerModel(app, name)

    def __eq__(self, other):
        return self.name == other.name and self.stats == other.stats and\
               self.active_tasks == other.active_tasks and\
               self.active_queues == other.active_queues and\
               self.revoked_tasks == other.revoked_tasks and\
               self.registered_tasks == other.registered_tasks and\
               self.scheduled_tasks == other.scheduled_tasks and\
               self.reserved_tasks == other.reserved_tasks and\
               self.conf == other.conf


class TaskModel(BaseModel):
    def __init__(self, app, task_id):
        super(TaskModel, self).__init__(app)

        task = app.events.state.tasks[task_id]

        self._fields = task._defaults.keys()
        for name, value in task.info(fields=self._fields).iteritems():
            setattr(self, name, value)

    @classmethod
    def get_task_by_id(cls, app, task_id):
        try:
            return TaskModel(app, task_id)
        except KeyError:
            return None

    @classmethod
    def iter_tasks(cls, app, limit=None, type=None, worker=None, state=None):
        i = 0
        events_state = app.events.state
        for uuid, task in events_state._sort_tasks_by_time(
                events_state.itertasks()):
            if type and task.name != type:
                continue
            if worker and task.worker.hostname != worker:
                continue
            if state and task.state != state:
                continue
            yield uuid, task
            i += 1
            if i == limit:
                break

    @classmethod
    def seen_task_types(cls, app):
        return app.events.state.task_types()

    def __dir__(self):
        return self._fields
