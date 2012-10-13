from __future__ import absolute_import

from tornado.web import StaticFileHandler

from .views.workers import (
        WorkersView,
        WorkerView,
        )

from .views.tasks import (
        TaskView,
        TasksView,
        )

from .views import auth

from .api import events
from .api import control
from .api import tasks
from .api import workers

from .views.update import (
        UpdateWorkers,
        )

from .views.monitor import (
        Monitor,
        SucceededTaskMonitor,
        FailedTaskMonitor,
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
    # Worker API
    (r"/api/workers", workers.ListWorkers),
    (r"/api/worker/shutdown/(.+)", control.WorkerShutDown),
    (r"/api/worker/pool/restart/(.+)", control.WorkerPoolRestart),
    (r"/api/worker/pool/grow/(.+)", control.WorkerPoolGrow),
    (r"/api/worker/pool/shrink/(.+)", control.WorkerPoolShrink),
    (r"/api/worker/pool/autoscale/(.+)", control.WorkerPoolAutoscale),
    (r"/api/worker/queue/add-consumer/(.+)", control.WorkerQueueAddConsumer),
    (r"/api/worker/queue/cancel-consumer/(.+)",
        control.WorkerQueueCancelConsumer),
    # Task API
    (r"/api/tasks", tasks.ListTasks),
    (r"/api/task/async-apply/(.+)", tasks.TaskAsyncApply),
    (r"/api/task/result/(.+)", tasks.TaskResult),
    (r"/api/task/timeout/(.+)", control.TaskTimout),
    (r"/api/task/rate-limit/(.+)", control.TaskRateLimit),
    (r"/api/task/revoke/(.+)", control.TaskRevoke),
    # Events WebSocket API
    (r"/api/task/events/task-sent/(.*)", events.TaskSent),
    (r"/api/task/events/task-received/(.*)", events.TaskReceived),
    (r"/api/task/events/task-started/(.*)", events.TaskStarted),
    (r"/api/task/events/task-succeeded/(.*)", events.TaskSucceeded),
    (r"/api/task/events/task-failed/(.*)", events.TaskFailed),
    (r"/api/task/events/task-revoked/(.*)", events.TaskRevoked),
    (r"/api/task/events/task-retried/(.*)", events.TaskRetried),
    # WebSocket Updates
    (r"/update-workers", UpdateWorkers),
    # Monitors
    (r"/monitor", Monitor),
    (r"/monitor/succeeded-tasks", SucceededTaskMonitor),
    (r"/monitor/failed-tasks", FailedTaskMonitor),
    # Static
    (r"/static/(.*)", StaticFileHandler,
                        {"path": APP_SETTINGS['static_path']}),
    # Auth
    (r"/login", auth.LoginHandler),
    (r"/logout", auth.LogoutHandler),

    # Error
    (r".*", NotFoundErrorHandler),
]
