import logging
import time

from tornado import web

from ..options import options
from ..views import BaseHandler

logger = logging.getLogger(__name__)


class WorkerView(BaseHandler):
    list_limit = 50

    @web.authenticated
    async def get(self, name):
        try:
            update = self.application.update_workers(workername=name)
            # wait for inspection only when the cache lacks something this page shows
            # cached workers render immediately and refresh in the background
            cached = self.application.workers.get(name, {})
            if any(method not in cached for method in self.application.inspector.inspect_methods):
                await update
        except Exception as e:
            logger.error(e)

        worker = self.application.workers.get(name)

        if worker is None:
            raise web.HTTPError(404, f"Unknown worker '{name}'")
        if 'stats' not in worker:
            raise web.HTTPError(404, f"Unable to get stats for '{name}' worker")

        worker = dict(worker, name=name)
        # Scheduled and revoked lists can hold thousands of entries, show the head
        limit = self.get_argument('limit', self.list_limit, type=int)
        for key, value in worker.items():
            if isinstance(value, list):
                worker[key] = value[:limit]

        self.render(
            "worker.html",
            worker=worker,
            read_only=self.application.options.read_only,
        )


# Every column the workers page can show, slug to header label
WORKER_COLUMNS = {
    'name': 'Worker',
    'status': 'Status',
    'active': 'Active',
    'task_received': 'Processed',
    'task_failed': 'Failed',
    'task_succeeded': 'Succeeded',
    'loadavg': 'Load Average',
}

COLUMN_ALIASES = {
    'task-received': 'task_received',
    'task-failed': 'task_failed',
    'task-succeeded': 'task_succeeded',
    'hostname': 'name',
    'worker': 'name',
}


def visible_worker_columns(workers_columns):
    "Slug and label of each column the workers page shows, in the order workers_columns lists them"
    result = []
    for raw_name in map(str.strip, workers_columns.split(',')):
        name = COLUMN_ALIASES.get(raw_name, raw_name)
        if name in WORKER_COLUMNS:
            result.append((name, WORKER_COLUMNS[name]))
    return result


class WorkersView(BaseHandler):
    @web.authenticated
    async def get(self):
        refresh = self.get_argument('refresh', default=False, type=bool)
        json = self.get_argument('json', default=False, type=bool)

        events = self.application.events.state

        if refresh:
            try:
                self.application.update_workers()
            except Exception:
                logger.exception('Failed to update workers')

        workers = {}
        for name, values in events.counter.items():
            if name not in events.workers:
                continue
            worker = events.workers[name]
            info = dict(values)
            info.update(self._as_dict(worker))
            info.update(status=worker.alive)
            workers[name] = info

        if options.purge_offline_workers is not None:
            timestamp = int(time.time())
            offline_workers = []
            for name, info in workers.items():
                if info.get('status', True):
                    continue

                heartbeats = info.get('heartbeats', [])
                last_seen = max(heartbeats) if heartbeats else \
                    getattr(events.workers[name], 'timestamp', None)
                if not last_seen or timestamp - int(last_seen) >= options.purge_offline_workers:
                    offline_workers.append(name)

            for name in offline_workers:
                workers.pop(name)

        available_hosts = sorted(set(name.split('@', 1)[1] if '@' in name else name for name in workers.keys()))
        configured_hosts = self.application.options.worker_hosts
        if configured_hosts:
            hosts = [h.strip() for h in configured_hosts.split(',') if h.strip()]
        else:
            hosts = available_hosts if len(available_hosts) > 1 else []

        if json:
            self.write({"data": list(workers.values())})
        else:
            self.render("workers.html",
                        workers=workers,
                        hosts=hosts,
                        columns=visible_worker_columns(self.application.options.workers_columns),
                        broker=self.application.broker_uri,
                        autorefresh=1 if self.application.options.auto_refresh else 0)

    @classmethod
    def _as_dict(cls, worker):
        return {k: getattr(worker, k) for k in worker._fields}
