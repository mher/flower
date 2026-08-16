import unittest
from unittest.mock import MagicMock, Mock

from flower.app import Flower


class TestFlower(unittest.TestCase):
    def test_broker_properties_cache_values_and_close_connections(self):
        app = Flower.__new__(Flower)
        app.capp = Mock()

        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.as_uri.side_effect = lambda include_password=False: (
            'amqp://guest:guest@localhost//' if include_password
            else 'amqp://guest:**@localhost//'
        )
        connection.transport.driver_type = 'amqp'
        app.capp.connection.return_value = connection

        self.assertEqual('amqp://guest:**@localhost//', app.broker_uri)
        self.assertEqual('amqp://guest:**@localhost//', app.broker_uri)
        self.assertEqual('amqp://guest:guest@localhost//', app.broker_uri_with_password)
        self.assertEqual('amqp://guest:guest@localhost//', app.broker_uri_with_password)
        self.assertEqual('amqp', app.transport)
        self.assertEqual('amqp', app.transport)

        self.assertEqual(3, app.capp.connection.call_count)
        self.assertEqual(3, connection.__enter__.call_count)
        self.assertEqual(3, connection.__exit__.call_count)
