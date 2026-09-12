from flower.views import BaseHandler
from tests.unit import AsyncHTTPTestCase


class CookieHandler(BaseHandler):
    def get(self):
        self.set_secure_cookie('user', 'user@example.com')
        self.finish('ok')


class SecureCookieTests(AsyncHTTPTestCase):
    def get_app(self):
        app = super().get_app()
        app.add_handlers(r'.*', [(r'/setcookie', CookieHandler)])
        return app

    def test_session_cookie_flags(self):
        cookie = self.fetch('/setcookie').headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)

    def test_xsrf_cookie_stays_readable(self):
        # The UI reads _xsrf from document.cookie
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.fetch('/', auth_username='user', auth_password='pass')
            xsrf = [c for c in r.headers.get_list('Set-Cookie')
                    if c.startswith('_xsrf=')]
            self.assertEqual(1, len(xsrf))
            self.assertNotIn('HttpOnly', xsrf[0])
