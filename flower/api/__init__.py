import tornado.web

from ..views import BaseHandler


class BaseApiHandler(BaseHandler):
    async def run_blocking(self, operation, target, func, *args,
                           connection_errors=(), **kwargs):
        return await self.application.blocking_runner.run(
            operation,
            target,
            func,
            *args,
            connection_errors=connection_errors,
            **kwargs,
        )

    def prepare(self):
        if not (self.application.options.basic_auth or self.application.options.auth) and not self.unauthenticated_api:
            raise tornado.web.HTTPError(
                401, "FLOWER_UNAUTHENTICATED_API environment variable is required to enable API without authentication")

    def write_error(self, status_code, **kwargs):
        exc_info = kwargs.get('exc_info')
        exc = exc_info[1] if exc_info else None
        message = exc.get_message() if isinstance(exc, tornado.web.HTTPError) else None
        if message:
            self.set_header('Content-Type', 'text/plain; charset=UTF-8')
            self.write(message)
        self.finish()
