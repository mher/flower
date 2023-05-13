import prometheus_client

from ..views import BaseHandler


class Metrics(BaseHandler):
    async def get(self):
        self.write(prometheus_client.generate_latest())
        self.set_header("Content-Type", "text/plain")


class Healthcheck(BaseHandler):
    async def get(self):
        self.write("OK")
