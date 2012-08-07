import sys

from ..api import BaseWebSocketHandler


EVENTS = ('task-sent', 'task-received','task-started','task-succeeded',
          'task-failed', 'task-revoked', 'task-retried')


def getClassName(eventname):
    return ''.join(map(lambda x:x[0].upper()+x[1:], eventname.split('-')))


# Dynamically generates handler classes
thismodule = sys.modules[__name__]
for event in EVENTS:
    classname = getClassName(event)
    setattr(thismodule, classname, type(classname, (BaseWebSocketHandler,), {}))


__all__ = map(getClassName, EVENTS)
__all__.append(getClassName)
