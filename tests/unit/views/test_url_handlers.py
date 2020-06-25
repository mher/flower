from tests.unit import AsyncHTTPTestCase
from flower.app import rewrite_handler
from tornado.web import url


class UrlsTests(AsyncHTTPTestCase):
    def test_dashboard_url(self):
        r = self.get('/dashboard')
        self.assertEqual(200, r.code)

    def test_root_url(self):
        r = self.get('/')
        self.assertEqual(200, r.code)

    def test_tasks_api_url(self):
        r = self.get('/api/tasks')
        self.assertEqual(200, r.code)


class URLPrefixTests(AsyncHTTPTestCase):
    def setUp(self):
        with self.mock_option('url_prefix', 'test_root'):
            super(URLPrefixTests, self).setUp()

    def test_tuple_handler_rewrite(self):
        r = self.get('/test_root/dashboard')
        self.assertEqual(200, r.code)

    def test_root_url(self):
        r = self.get('/test_root/')
        self.assertEqual(200, r.code)

    def test_tasks_api_url(self):
        r = self.get('/test_root/api/tasks')
        self.assertEqual(200, r.code)

    def test_base_url_no_longer_working(self):
        r = self.get('/dashboard')
        self.assertNotEqual(200, r.code)


class RewriteHandlerTests(AsyncHTTPTestCase):
    def target(self):
        return None

    def test_url_rewrite_using_URLSpec(self):
        old_handler = url(r"/", self.target, name='test')
        new_handler = rewrite_handler(old_handler, 'test_root')
        self.assertIsInstance(new_handler, url)
        self.assertTrue(new_handler.regex.match('/test_root/'))
        self.assertFalse(new_handler.regex.match('/'))
        self.assertFalse(new_handler.regex.match('/'))

    def test_url_rewrite_using_tuple(self):
        old_handler = (r"/", self.target)
        new_handler = rewrite_handler(old_handler, 'test_root')
        self.assertIsInstance(new_handler, tuple)
        self.assertEqual(new_handler[0], '/test_root/')
