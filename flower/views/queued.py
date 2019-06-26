import json
import traceback

from tornado import web, gen

from flower.api.control import ControlHandler
from flower.utils.broker import Broker
from flower.utils.search import parse_queued_search_terms
from flower.views import BaseHandler


class QueuedView(BaseHandler):
    @web.authenticated
    def get(self):
        app = self.application
        capp = self.application.capp

        time = 'natural-time' if app.options.natural_time else 'time'
        if capp.conf.CELERY_TIMEZONE:
            time += '-' + str(capp.conf.CELERY_TIMEZONE)

        self.render(
            "queued.html",
            tasks=[],
            columns=app.options.queued_columns,
            time=time,
        )


class TasksQueuedDataTable(BaseHandler):
    @web.authenticated
    @gen.coroutine
    def get(self):
        app = self.application
        broker_options = self.capp.conf.BROKER_TRANSPORT_OPTIONS

        draw = self.get_argument('draw', type=int)
        start = self.get_argument('start', type=int)
        length = self.get_argument('length', type=int)
        search = self.get_argument("search[value]", str)
        parsed_search = parse_queued_search_terms(search)
        queue_names = parsed_search.get("queue")

        http_api = None
        if app.transport == 'amqp' and app.options.broker_api:
            http_api = app.options.broker_api

        try:
            broker = Broker(app.capp.connection().as_uri(include_password=True),
                            http_api=http_api, broker_options=broker_options)
        except NotImplementedError:
            raise web.HTTPError(
                404, "'%s' broker is not supported" % app.transport)
        try:
            if not queue_names:
                queue_names = ControlHandler.get_active_queue_names()
            if not queue_names:
                queue_names = {self.capp.conf.CELERY_DEFAULT_QUEUE, } |\
                              {q.name for q in self.capp.conf.CELERY_QUEUES or [] if q.name}
            queues = yield broker.queues(sorted(queue_names))
            tasks_on_queues = []
            for queue in queue_names:
                tasks = yield broker.tasks_on_queue(queue, start, length)
                tasks_on_queues.extend(tasks)
            for idx, task in enumerate(tasks_on_queues):
                tasks_on_queues[idx] = {
                    "name": task["headers"]["task"],
                    "uuid": task["headers"]["id"],
                    "parent_id": task["headers"].get("parent_id") or "N/A",
                    "root_id": task["headers"].get("root_id") or "N/A",
                    "args": task["headers"]["argsrepr"],
                    "kwargs": task["headers"]["kwargsrepr"],
                    "delivery_info": json.dumps(task["properties"]["delivery_info"]),
                    "body": task["body"],
                }
        except Exception as e:
            raise web.HTTPError(404, "Unable to get queues: '%s', %s" % (e, traceback.format_exc()))

        time = 'natural-time' if app.options.natural_time else 'time'
        if app.capp.conf.CELERY_TIMEZONE:
            time += '-' + str(app.capp.conf.CELERY_TIMEZONE)
        to_write = dict(draw=draw,
                        data=tasks_on_queues,
                        recordsTotal=sum(queue_item["messages"] for queue_item in queues),
                        recordsFiltered=sum(queue_item["messages"] for queue_item in queues),
                        )
        self.write(to_write)

    @web.authenticated
    def post(self):
        return self.get()
