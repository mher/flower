import os
import time
from datetime import datetime

from celery import Celery


app = Celery("tasks",
             broker=os.environ.get('CELERY_BROKER_URL', 'redis://'),
             backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis'))
app.conf.accept_content = ['pickle', 'json', 'msgpack', 'yaml']
app.conf.worker_send_task_events = True


@app.task
def add(x, y):
    return x + y


@app.task
def sleep(seconds):
    time.sleep(seconds)


@app.task
def echo(msg, timestamp=False):
    return "%s: %s" % (datetime.now(), msg) if timestamp else msg


@app.task
def error(msg):
    raise Exception(msg)


if __name__ == "__main__":
    app.start()
