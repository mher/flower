from __future__ import absolute_import

import base64
import uuid

from .. import __version__


def gen_cookie_secret():
    return base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)


def bugreport():
    try:
        import celery
        return 'flower   -> %s' % __version__ + celery.bugreport()
    except (ImportError, AttributeError):
        return 'Unknown Celery version'
