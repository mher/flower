from __future__ import absolute_import

from tornado.web import StaticFileHandler

from .views.worker import (
        WorkersView,
        WorkerView,
        )

from .views.tasks import (
        TaskView,
        TasksView,
        )

from .views.control import (
        ShutdownWorker,
        RestartWorkerPool,
        WorkerPoolGrow,
        WorkerPoolShrink,
        WorkerPoolAutoscale,
        WorkerQueueAddConsumer,
        WorkerQueueCancelConsumer,
        TaskRateLimit,
        TaskTimout,
        )

from .views.update import (
        UpdateWorkers,
        )

from .views.error import NotFoundErrorHandler
from .settings import APP_SETTINGS


handlers = [
    # App
    (r"/", WorkersView),
    (r"/workers", WorkersView),
    (r"/worker/(.+)", WorkerView),
    (r"/task/(.+)", TaskView),
    (r"/tasks", TasksView),
    # Commands
    (r"/shut-down-worker/(.+)", ShutdownWorker),
    (r"/restart-pool-worker/(.+)", RestartWorkerPool),
    (r"/worker-pool-grow/(.+)", WorkerPoolGrow),
    (r"/worker-pool-shrink/(.+)", WorkerPoolShrink),
    (r"/worker-pool-autoscale/(.+)", WorkerPoolAutoscale),
    (r"/worker-queue-add-consumer/(.+)", WorkerQueueAddConsumer),
    (r"/worker-queue-cancel-consumer/(.+)", WorkerQueueCancelConsumer),
    (r"/task-timeout/(.+)", TaskTimout),
    (r"/task-rate-limit/(.+)", TaskRateLimit),
    # WebSocket Updates
    (r"/update-workers", UpdateWorkers),
    # Static
    (r"/static/(.*)", StaticFileHandler,
                        {"path": APP_SETTINGS['static_path']}),
    # Error
    (r".*", NotFoundErrorHandler),
]
