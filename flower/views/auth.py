import tornado.web
import tornado.auth

from ..views import BaseHandler


class LoginHandler(BaseHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'Google auth failed')
        if user['email'] not in self.application.auth:
            raise tornado.web.HTTPError(404, "Access denied to '{email}'. "
                    "Please use another account or ask your admin to "
                    "add your email to flower --auth".format(**user))

        self.set_secure_cookie("user", str(user['email']))
        self.redirect(self.get_argument('next', '/'))


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.render('404.html', message='Successfully logged out!')
