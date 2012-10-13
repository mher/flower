from __future__ import absolute_import

from os.path import join, abspath, dirname

from .utils import gen_cookie_secret


PROJECT_ROOT = abspath(dirname(__file__))

APP_SETTINGS = dict(
    template_path=join(PROJECT_ROOT, "templates"),
    static_path=join(PROJECT_ROOT, "static"),
    cookie_secret=gen_cookie_secret(),
    login_url='/login',
)

PAGE_UPDATE_INTERVAL = 2000
CELERY_EVENTS_ENABLE_INTERVAL = 5000
CELERY_INSPECT_TIMEOUT = 1000
