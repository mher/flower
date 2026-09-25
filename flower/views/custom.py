import mimetypes
import os

from tornado import web


class CustomAssetHandler(web.RequestHandler):
    def get(self, asset_type):
        options = self.application.options
        asset_map = {
            'logo': getattr(options, 'brand_logo', None),
            'favicon': getattr(options, 'brand_favicon', None),
            'css': getattr(options, 'custom_css', None),
        }
        file_path = asset_map.get(asset_type)
        if not file_path or not os.path.isfile(file_path):
            raise web.HTTPError(404, f"Custom {asset_type} not found")

        content_type, _ = mimetypes.guess_type(file_path)
        if asset_type == 'css':
            content_type = 'text/css; charset=utf-8'
        elif not content_type:
            content_type = 'application/octet-stream'

        self.set_header("Content-Type", content_type)
        with open(file_path, "rb") as f:
            self.write(f.read())
