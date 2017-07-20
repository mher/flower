import json
import logging
from datetime import datetime

import pg8000

logger = logging.getLogger(__name__)
connection = None

_all_tables = """
SELECT * FROM information_schema.tables
WHERE table_schema = 'public'
"""

_schema = [
    """CREATE TABLE events
    (
        id TIMESTAMP PRIMARY KEY,
        data JSONB NOT NULL
    )""",
    """CREATE INDEX event_index ON events USING GIN (data)"""
]

_add_event = """INSERT INTO events (id, data) VALUES (%s, %s)"""

_all_events = """SELECT data FROM events ORDER BY id ASC"""


def event_callback(state, event):
    if event['type'] == 'worker-heartbeat':
        return

    cursor = connection.cursor()
    try:
        cursor.execute(_add_event, (
            datetime.fromtimestamp(event['timestamp']),
            json.dumps(event)
        ))
        connection.commit()
    finally:
        cursor.close()


def open_connection(user, password, database, host, port, use_ssl):
    global connection
    connection = pg8000.connect(
        user=user, password=password, database=database,
        host=host, port=port, ssl=use_ssl
    )

    # Create schema if database is empty
    cursor = connection.cursor()
    try:
        cursor.execute(_all_tables)
        tables = cursor.fetchone()
        if tables is None:
            logger.debug('Database empty, executing schema definition.')
            for statement in _schema:
                cursor.execute(statement)
    finally:
        cursor.close()


def close_connection():
    global connection
    if connection is not None:
        connection.close()
        connection = None


def get_all_events():
    cursor = connection.cursor()
    try:
        cursor.execute(_all_events)
        for row in cursor:
            yield row[0]
    finally:
        cursor.close()
