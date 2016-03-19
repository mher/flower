from celery.utils import uuid
from celery.events import Event


try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser
import xml.etree.ElementTree as ET


class HtmlTableParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)
        self.table = ''
        self.inTable = False

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.inTable = True
        if self.inTable:
            self.table += '<%s' % tag
            for attr in attrs:
                self.table += ' %s="%s"' % attr
            self.table += '>'

    def handle_endtag(self, tag):
        if self.inTable:
            self.table += '</%s>' % tag
            if tag == 'table':
                self.inTable = False

    def handle_data(self, data):
        if self.inTable:
            self.table += data

    def parse(self, source):
        self.feed(source)

    def query(self, pattern):
        root = ET.fromstring(self.table)
        return root.findall(pattern)

    def rows(self):
        return self.query('tbody/tr')

    def get_row(self, row_id):
        rows = self.query('tbody/tr')
        for r in rows:
            if r.attrib.get('id') == row_id:
                cells = r.findall('td')
                return list(map(lambda x: getattr(x, 'text'), cells))


def task_succeeded_events(worker, id=None, name=None):
    id = id or uuid()
    name = name or 'sometask'
    return [Event('task-received', uuid=id, name=name,
                  args='(2, 2)', kwargs="{'foo': 'bar'}",
                  retries=0, eta=None, hostname=worker),
            Event('task-started', uuid=id, hostname=worker),
            Event('task-succeeded', uuid=id, result='4',
                  runtime=0.1234, hostname=worker)]


def task_failed_events(worker, id=None, name=None):
    id = id or uuid()
    name = name or 'sometask'
    return [Event('task-received', uuid=id, name=name,
                  args='(2, 2)', kwargs="{'foo': 'bar'}",
                  retries=0, eta=None, hostname=worker),
            Event('task-started', uuid=id, hostname=worker),
            Event('task-failed', uuid=id, exception="KeyError('foo')",
                  traceback='line 1 at main', hostname=worker)]
