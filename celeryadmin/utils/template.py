from __future__ import absolute_import

import re

from datetime import datetime

KEYWORDS = map(str.lower, ('SSL', 'URI', 'URL'))


def humanize(obj, type=None):
    if type in ('GUID', 'args', 'kwargs'):
        pass
    elif obj is None:
        obj = ''
    elif type == 'time':
        obj = datetime.fromtimestamp(float(obj)).strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, basestring):
        obj = obj.replace('-', ' ').replace('_', ' ')
        obj = re.sub('|'.join(KEYWORDS),
                     lambda m: m.group(0).upper(), obj)
        if obj:
            obj = obj[0].upper() + obj[1:]
    elif isinstance(obj, list):
        if all(map(lambda x: isinstance(x, (int, float, basestring)), obj)):
            obj = ', '.join(map(str, obj))
    return obj
