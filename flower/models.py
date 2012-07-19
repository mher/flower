from __future__ import absolute_import
from __future__ import with_statement

from collections import OrderedDict

from .state import state
from .events import tasks
from .events import state as event_state


class BaseModel(object):
    def __eq__(self, other):
        raise NotImplementedError

    def __ne__(self, other):
        return not self.__eq__(other)


class WorkersModel(BaseModel):
    def __init__(self, state):
        super(WorkersModel, self).__init__()
        self.workers = OrderedDict()
        self.initialize(state)

    def initialize(self, state):
        for workername, stat in sorted(state.stats.iteritems()):
            self.workers[workername] = dict(
                    status=(workername in state.ping),
                    concurrency=stat['pool']['max-concurrency'],
                    completed_tasks=sum(stat['total'].itervalues()),
                    running_tasks=len(state.active_tasks.get(workername, [])),
                    queues=map(lambda x: x['name'],
                               state.active_queues.get(workername, [])),
                    )

    @classmethod
    def get_latest(cls):
        return WorkersModel(state)

    @classmethod
    def get_workers(cls):
        return state.stats.keys()

    @classmethod
    def is_worker(cls, workername):
        return WorkerModel(workername, state) is not None

    def __eq__(self, other):
        return other is not None and self.workers == other.workers


class WorkerModel(BaseModel):
    def __init__(self, workername, state):
        super(BaseModel, self).__init__()
        self.initialize(workername, state)

    def initialize(self, name, state):
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
    def get_worker(self, name):
        if name not in state.stats:
            return None
        return WorkerModel(name, state)

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
    def __init__(self, task_id):
        super(BaseModel, self).__init__()

        task = tasks[task_id]

        self._fields = task._defaults.keys()
        for name, value in task.info(fields=self._fields).iteritems():
            setattr(self, name, value)

    @classmethod
    def get_task_by_id(cls, task_id):
        try:
            return TaskModel(task_id)
        except KeyError:
            return None

    @classmethod
    def iter_tasks(cls, limit=None, type=None, worker=None):
        i = 0
        for uuid, task in event_state._sort_tasks_by_time(
                event_state.itertasks()):
            if type and task.name != type:
                continue
            if worker and task.worker.hostname != worker:
                continue
            yield uuid, task
            i += 1
            if i == limit:
                break

    @classmethod
    def seen_task_types(cls):
        return event_state.task_types()

    def __dir__(self):
        return self._fields
