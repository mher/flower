import logging

import pg8000

logger = logging.getLogger(__name__)
connection = None


def event_callback(state, event):
    if event['type'] == 'worker-heartbeat':
        return

    print(event)


def open_connection(user, password, database, host, port, use_ssl):
    global connection
    connection = pg8000.connect(
        user=user, password=password, database=database,
        host=host, port=port, ssl=use_ssl
    )


def close_connection():
    global connection
    if connection is not None:
        connection.close()
        connection = None
