from __future__ import absolute_import

import re

from datetime import datetime

KEYWORDS_UP = ('ssl', 'uri', 'url', 'uuid', 'eta')
KEYWORDS_DOWN = ('args', 'kwargs')
UUID_REGEX = re.compile(r'^[\w]{8}(-[\w]{4}){3}-[\w]{12}$')


def humanize(obj, type=None, length=None):
    if obj is None:
        obj = ''
    elif type == 'time':
        obj = datetime.fromtimestamp(float(obj)).strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, basestring) and not re.match(UUID_REGEX, obj):
        obj = obj.replace('-', ' ').replace('_', ' ')
        obj = re.sub('|'.join(KEYWORDS_UP),
                     lambda m: m.group(0).upper(), obj)
        if obj and obj not in KEYWORDS_DOWN:
            obj = obj[0].upper() + obj[1:]
    elif isinstance(obj, list):
        if all(map(lambda x: isinstance(x, (int, float, basestring)), obj)):
            obj = ', '.join(map(str, obj))
    if length is not None and len(obj) > length:
        obj = obj[:length - 4] + ' ...'
    return obj
