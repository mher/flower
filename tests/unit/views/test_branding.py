import os
import tempfile
from tests.unit import AsyncHTTPTestCase


class TestBranding(AsyncHTTPTestCase):
    def test_default_branding(self):
        r = self.get('/')
        self.assertEqual(200, r.code)
        self.assertIn(b'<title>Workers \xc2\xb7 Flower</title>', r.body)
        self.assertIn(b'<span>Flower</span>', r.body)
        self.assertIn(b'favicon.ico', r.body)

    def test_custom_app_name_and_urls(self):
        with self.mock_option('app_name', 'MyCustomPlatform'), \
             self.mock_option('brand_logo', 'https://cdn.example.com/logo.svg'), \
             self.mock_option('brand_favicon', 'https://cdn.example.com/favicon.png'), \
             self.mock_option('custom_css', 'https://cdn.example.com/theme.css'), \
             self.mock_option('primary_color', '#ff5500'), \
             self.mock_option('secondary_color', '#223344'):
            r = self.get('/')
            self.assertEqual(200, r.code)
            self.assertIn(b'<title>Workers \xc2\xb7 MyCustomPlatform</title>', r.body)
            self.assertIn(b'<span>MyCustomPlatform</span>', r.body)
            self.assertIn(b'src="https://cdn.example.com/logo.svg"', r.body)
            self.assertIn(b'href="https://cdn.example.com/favicon.png"', r.body)
            self.assertIn(b'href="https://cdn.example.com/theme.css"', r.body)
            self.assertIn(b'--bs-primary: #ff5500;', r.body)
            self.assertIn(b'--bs-secondary: #223344;', r.body)

    def test_custom_local_asset_serving(self):
        with tempfile.NamedTemporaryFile(suffix='.css', delete=False) as f:
            f.write(b'/* custom css content */\nbody { background: red; }')
            f.flush()
            css_path = f.name

        try:
            with self.mock_option('custom_css', css_path):
                r = self.get('/')
                self.assertEqual(200, r.code)
                self.assertIn(b'href="/custom-asset/css"', r.body)

                asset_r = self.get('/custom-asset/css')
                self.assertEqual(200, asset_r.code)
                self.assertIn(b'text/css', asset_r.headers.get('Content-Type', '').encode())
                self.assertIn(b'body { background: red; }', asset_r.body)
        finally:
            if os.path.exists(css_path):
                os.remove(css_path)
