import logging
import time

from tornado import web

from ..options import options
from ..views import BaseHandler

logger = logging.getLogger(__name__)


class WorkerView(BaseHandler):
    @web.authenticated
    async def get(self, name):
        try:
            self.application.update_workers(workername=name)
        except Exception as e:
            logger.error(e)

        worker = self.application.workers.get(name)

        if worker is None:
            raise web.HTTPError(404, f"Unknown worker '{name}'")
        if 'stats' not in worker:
            raise web.HTTPError(404, f"Unable to get stats for '{name}' worker")

        self.render("worker.html", worker=dict(worker, name=name))


class WorkersView(BaseHandler):
    @web.authenticated
    async def get(self):
        refresh = self.get_argument('refresh', default=False, type=bool)
        json = self.get_argument('json', default=False, type=bool)

        events = self.application.events.state

        if refresh:
            try:
                self.application.update_workers()
            except Exception as e:
                logger.exception('Failed to update workers: %s', e)

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
                last_heartbeat = int(max(heartbeats)) if heartbeats else None
                if not last_heartbeat or timestamp - last_heartbeat > options.purge_offline_workers:
                    offline_workers.append(name)

            for name in offline_workers:
                workers.pop(name)

        if json:
            self.write(dict(data=list(workers.values())))
        else:
            self.render("workers.html",
                        workers=workers,
                        broker=self.application.capp.connection().as_uri(),
                        autorefresh=1 if self.application.options.auto_refresh else 0)

    @classmethod
    def _as_dict(cls, worker):
        if hasattr(worker, '_fields'):
            return dict((k, getattr(worker, k)) for k in worker._fields)
        return cls._info(worker)

    @classmethod
    def _info(cls, worker):
        _fields = ('hostname', 'pid', 'freq', 'heartbeats', 'clock',
                   'active', 'processed', 'loadavg', 'sw_ident',
                   'sw_ver', 'sw_sys')

        def _keys():
            for key in _fields:
                value = getattr(worker, key, None)
                if value is not None:
                    yield key, value

        return dict(_keys())
