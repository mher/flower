import os

import prometheus_client.multiprocess

from ..views import BaseHandler


class Metrics(BaseHandler):
    def _get_registry(self):
        if not ("PROMETHEUS_MULTIPROC_DIR" in os.environ
                or "prometheus_multiproc_dir" in os.environ):
            return prometheus_client.REGISTRY

        registry = prometheus_client.CollectorRegistry()
        prometheus_client.multiprocess.MultiProcessCollector(registry)
        return registry

    async def get(self):
        self.write(prometheus_client.generate_latest(self._get_registry()))
        self.set_header("Content-Type", "text/plain")


class Healthcheck(BaseHandler):
    async def get(self):
        self.write("OK")
