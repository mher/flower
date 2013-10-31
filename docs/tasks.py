from celery import Celery
from time import sleep

celery = Celery()
celery.config_from_object({
    'BROKER_URL': 'amqp://10.0.2.2',
    'CELERY_RESULT_BACKEND': 'amqp://',
    'CELERYD_POOL_RESTARTS': True,
})


@celery.task
def add(x, y):
    return x + y


@celery.task
def sub(x, y):
    sleep(30)  # Simulate work
    return x - y
