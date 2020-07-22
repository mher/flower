import re
import time

from celery import current_app
from datetime import datetime
from datetime import timedelta
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from humanize import naturaltime, naturaldelta
from pytz import timezone, utc


KEYWORDS_UP = ('ssl', 'uri', 'url', 'uuid', 'eta')
KEYWORDS_DOWN = ('args', 'kwargs')
UUID_REGEX = re.compile(r'^[\w]{8}(-[\w]{4}){3}-[\w]{12}$')


def format_time(time, tz):
    dt = datetime.fromtimestamp(time, tz=tz)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f %Z")


def unix_now():
    return time.time()


def humanize(obj, type=None, length=None):
    if obj is None:
        obj = ''
    elif type and type.startswith('time'):
        tz = type[len('time'):].lstrip('-')
        tz = timezone(tz) if tz else getattr(current_app, 'timezone', '') or utc
        obj = format_time(float(obj), tz) if obj else ''
    elif type and type.startswith('natural-time'):
        tz = type[len('natural-time'):].lstrip('-')
        tz = timezone(tz) if tz else getattr(current_app, 'timezone', '') or utc
        delta = datetime.now(tz) - datetime.fromtimestamp(float(obj), tz)
        if delta < timedelta(days=1):
            obj = naturaltime(delta)
        else:
            obj = format_time(float(obj), tz) if obj else ''
    elif type == 'elapsed':
        obj = naturaldelta(obj)
    elif isinstance(obj, str) and not re.match(UUID_REGEX, obj):
        obj = obj.replace('-', ' ').replace('_', ' ')
        obj = re.sub('|'.join(KEYWORDS_UP),
                     lambda m: m.group(0).upper(), obj)
        if obj and obj not in KEYWORDS_DOWN:
            obj = obj[0].upper() + obj[1:]
    elif isinstance(obj, list):
        if all(isinstance(x, (int, float, str)) for x in obj):
            obj = ', '.join(map(str, obj))
    if length is not None and len(obj) > length:
        obj = obj[:length - 4] + ' ...'
    return obj


def sort_url(name, key, sort_by, params=None, class_name='sort'):
    new_params = {}
    extra_class = ''
    title = 'Order by %s DESC' % name
    if params:
        new_params.update(params)

    if sort_by == key:
        extra_class = 'asc'
    if sort_by == '-' + key:
        extra_class = 'desc'
        title = 'Order by %s ASC' % name
    if not sort_by or sort_by == key or sort_by.lstrip('-') != key:
        new_params.update({'sort': '-' + key})
    else:
        new_params.update({'sort': key})

    return '<a class="%s %s" href="?%s" title="%s">%s</a>' % (
        class_name, extra_class, urlencode(new_params),
        title, name
    )
