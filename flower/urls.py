import os

from tornado.web import StaticFileHandler, url

from .api import control
from .api import tasks
from .api import workers
from .views import auth
from .views import monitor
from .views.broker import BrokerView
from .views.workers import WorkerView
from .views.tasks import TaskView, TasksView, TasksDataTable
from .views.error import NotFoundErrorHandler
from .views.dashboard import DashboardView
from .utils import gen_cookie_secret


settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "templates"),
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    cookie_secret=gen_cookie_secret(),
    static_url_prefix='/static/',
    login_url='/login',
)


handlers = [
    # App
    url(r"/", DashboardView, name='main'),
    url(r"/dashboard", DashboardView, name='dashboard'),
    url(r"/worker/(.+)", WorkerView, name='worker'),
    url(r"/task/(.+)", TaskView, name='task'),
    url(r"/tasks", TasksView, name='tasks'),
    url(r"/tasks/datatable", TasksDataTable),
    url(r"/broker", BrokerView, name='broker'),
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
    (r"/api/task/types", tasks.ListTaskTypes),
    (r"/api/queues/length", tasks.GetQueueLengths),
    (r"/api/task/info/(.*)", tasks.TaskInfo),
    (r"/api/task/apply/(.+)", tasks.TaskApply),
    (r"/api/task/async-apply/(.+)", tasks.TaskAsyncApply),
    (r"/api/task/send-task/(.+)", tasks.TaskSend),
    (r"/api/task/result/(.+)", tasks.TaskResult),
    (r"/api/task/abort/(.+)", tasks.TaskAbort),
    (r"/api/task/timeout/(.+)", control.TaskTimout),
    (r"/api/task/rate-limit/(.+)", control.TaskRateLimit),
    (r"/api/task/revoke/(.+)", control.TaskRevoke),
    # Metrics
    (r"/metrics", monitor.Metrics),
    (r"/healthcheck", monitor.Healthcheck),
    # Static
    (r"/static/(.*)", StaticFileHandler,
     {"path": settings['static_path']}),
    # Auth
    (r"/login", auth.LoginHandler),

    # Error
    (r".*", NotFoundErrorHandler),
]
