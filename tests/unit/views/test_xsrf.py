import os
from unittest.mock import patch

from tests.unit import AsyncHTTPTestCase


class XsrfProtectionTests(AsyncHTTPTestCase):
    def test_cookie_session_post_without_token_is_blocked(self):
        # OAuth (cookie) mode: a state-changing POST without an XSRF token is
        # rejected before it reaches the handler.
        with self.mock_option('auth', '.*@example.com'):
            r = self.post('/api/worker/shutdown/test', body={})
            self.assertEqual(403, r.code)
            self.assertIn(b'_xsrf', r.body)

    def test_header_auth_needs_no_token(self):
        # Scripted clients are not required to carry a token, so they reach
        # auth (401) rather than the XSRF check (403).
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          auth_username='user', auth_password='wrong')
            self.assertEqual(401, r.code)
            self.assertNotIn(b'_xsrf', r.body)

    @patch.dict(os.environ, {'FLOWER_UNAUTHENTICATED_API': 'true'})
    def test_unauthenticated_server_needs_no_token(self):
        # No auth configured: nothing to protect, scripts keep working.
        r = self.post('/api/worker/shutdown/test', body={})
        self.assertNotEqual(403, r.code)

    def test_basic_auth_cross_site_post_is_blocked(self):
        # Browsers attach cached Basic credentials cross-site
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Sec-Fetch-Site': 'cross-site'},
                          auth_username='user', auth_password='pass')
            self.assertEqual(403, r.code)

    def test_basic_auth_cross_origin_post_is_blocked(self):
        # Browsers predating fetch metadata still send Origin
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Origin': 'http://evil.example'},
                          auth_username='user', auth_password='pass')
            self.assertEqual(403, r.code)

    def test_basic_auth_navigation_post_is_blocked(self):
        # Only the UI talking to itself is accepted on unsafe methods
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Sec-Fetch-Site': 'none'},
                          auth_username='user', auth_password='pass')
            self.assertEqual(403, r.code)

    def test_basic_auth_same_origin_post_is_allowed(self):
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Sec-Fetch-Site': 'same-origin'},
                          auth_username='user', auth_password='pass')
            self.assertEqual(404, r.code)

    def test_basic_auth_matching_origin_is_allowed(self):
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Origin': self.get_url('').rstrip('/')},
                          auth_username='user', auth_password='pass')
            self.assertEqual(404, r.code)

    def test_fetch_metadata_wins_over_mismatched_origin(self):
        # A Host-rewriting proxy must not 403 the UI's own requests
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Sec-Fetch-Site': 'same-origin',
                                   'Origin': 'http://public.example'},
                          auth_username='user', auth_password='pass')
            self.assertEqual(404, r.code)

    def test_cookie_session_cross_site_post_is_blocked(self):
        with self.mock_option('auth', '.*@example.com'):
            r = self.post('/api/worker/shutdown/test', body={},
                          headers={'Sec-Fetch-Site': 'cross-site'})
            self.assertEqual(403, r.code)

    @patch.dict(os.environ, {'FLOWER_UNAUTHENTICATED_API': 'true'})
    def test_unauthenticated_server_allows_cross_site(self):
        # CORS is deliberately open without credentials
        r = self.post('/api/worker/shutdown/test', body={},
                      headers={'Sec-Fetch-Site': 'cross-site'})
        self.assertNotEqual(403, r.code)

    def test_full_page_load_sets_xsrf_cookie(self):
        # The UI relies on the _xsrf cookie being present so its AJAX calls can
        # echo the token back.
        with self.mock_option('basic_auth', ['user:pass']):
            r = self.fetch('/', auth_username='user', auth_password='pass')
            self.assertEqual(200, r.code)
            self.assertIn('_xsrf', r.headers.get('Set-Cookie', ''))
