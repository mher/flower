from __future__ import absolute_import

import re
import sys
import time

from datetime import datetime
from datetime import timedelta
from babel.dates import format_timedelta


PY2 = sys.version_info[0] == 2
if not PY2:
    string_types = (str,)
else:
    string_types = (str, unicode)


KEYWORDS_UP = ('ssl', 'uri', 'url', 'uuid', 'eta')
KEYWORDS_DOWN = ('args', 'kwargs')
UUID_REGEX = re.compile(r'^[\w]{8}(-[\w]{4}){3}-[\w]{12}$')


def format_time(time):
    dt = datetime.fromtimestamp(time)
    return '%s.%s' % (
        dt.strftime("%Y-%m-%d %H:%M:%S"), dt.microsecond)


def humanize(obj, type=None, length=None):
    if obj is None:
        obj = ''
    elif type == 'time':
        obj = format_time(float(obj)) if obj else ''
    elif type == 'natural-time':
        delta = time.time() - float(obj)
        if timedelta(seconds=delta) < timedelta(days=1):
            obj = format_timedelta(delta, locale='en_US') + ' ago'
        else:
            obj = format_time(float(obj)) if obj else ''
    elif isinstance(obj, string_types) and not re.match(UUID_REGEX, obj):
        obj = obj.replace('-', ' ').replace('_', ' ')
        obj = re.sub('|'.join(KEYWORDS_UP),
                     lambda m: m.group(0).upper(), obj)
        if obj and obj not in KEYWORDS_DOWN:
            obj = obj[0].upper() + obj[1:]
    elif isinstance(obj, list):
        if all(isinstance(x, (int, float) + string_types) for x in obj):
            obj = ', '.join(map(str, obj))
    if length is not None and len(obj) > length:
        obj = obj[:length - 4] + ' ...'
    return obj
