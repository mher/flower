from unittest import TestCase
from unittest.mock import Mock

from kombu.exceptions import OperationalError

from flower.inspector import Inspector


# pylint: disable=protected-access
class InspectorTests(TestCase):
    def test_logs_broker_failure_without_propagating_it(self):
        capp = Mock()
        capp.control.inspect.return_value.registered.side_effect = (
            OperationalError('broker is down'))
        inspector = Inspector(Mock(), capp, timeout=1)

        with self.assertLogs('flower.inspector', level='WARNING') as logs:
            inspector._inspect('registered', None)

        self.assertEqual(
            'WARNING:flower.inspector:'
            'Inspect method registered failed: broker is down',
            logs.output[0],
        )

    def test_handles_transport_specific_connection_error(self):
        class TransportConnectionError(Exception):
            pass

        capp = Mock()
        capp.control.inspect.return_value.active.side_effect = (
            TransportConnectionError('connection closed by server'))
        connection = capp.connection_for_read.return_value
        connection.recoverable_connection_errors = (
            TransportConnectionError,)
        inspector = Inspector(Mock(), capp, timeout=1)

        with self.assertLogs('flower.inspector', level='WARNING') as logs:
            inspector._inspect('active', None)

        self.assertEqual(
            'WARNING:flower.inspector:'
            'Inspect method active failed: connection closed by server',
            logs.output[0],
        )
        connection.close.assert_called_once_with()
