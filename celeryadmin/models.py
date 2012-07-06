from __future__ import absolute_import

from collections import OrderedDict

from .state import state


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
                    running_tasks=len(state.active_tasks[workername]),
                    queues=map(lambda x: x['name'],
                               state.active_queues[workername]),
                    )

    @classmethod
    def get_latest(cls):
        return WorkersModel(state)

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
        self.active_tasks = state.active_tasks[name]
        self.active_queues = state.active_queues[name]
        self.revoked_tasks = state.revoked_tasks[name]
        self.registered_tasks = filter(lambda x: not x.startswith('celery.'),
                                       state.registered_tasks[name])
        self.reserved_tasks = state.reserved_tasks[name]

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
               self.reserved_tasks == other.reserved_tasks
