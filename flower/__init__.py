from __future__ import absolute_import

VERSION = (0, 7, 0)
__version__ = '.'.join(map(str, VERSION)) + '-dev'

from .app import Flower  # noqa
