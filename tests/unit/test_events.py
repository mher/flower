import pickle
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from celery import Celery
from flower.events import Events, EventsState
from tornado.ioloop import IOLoop


class TestEventsRedisStateStorage(unittest.TestCase):
    """Test Redis state storage functionality for Celery Flower"""

    def setUp(self):
        self.capp = Celery()
        self.io_loop = IOLoop.current()

        self.mock_redis = MagicMock()
        self.mock_redis_client = MagicMock()
        self.mock_redis.Redis.from_url.return_value = self.mock_redis_client
        self.mock_redis_client.get.return_value = None

        self.mock_shelve = MagicMock()
        self.mock_shelve_db = MagicMock()
        self.mock_shelve.open.return_value = self.mock_shelve_db

    def _create_events_with_redis(self, db_url="redis://localhost:6379/0", **kwargs):
        """Helper method to create Events instance with mocked Redis"""
        with patch("flower.events.redis", self.mock_redis):
            return Events(self.capp, self.io_loop, db=db_url, persistent=True, **kwargs)

    def _create_events_with_shelve(self, db_path, **kwargs):
        """Helper method to create Events instance with mocked shelve"""
        with patch("flower.events.shelve", self.mock_shelve):
            return Events(
                self.capp, self.io_loop, db=db_path, persistent=True, **kwargs
            )

    def test_redis_client_initialization_with_redis_url(self):
        """Test that redis client is initialized when db starts with redis://"""
        events = self._create_events_with_redis("redis://localhost:6379/0")

        self.mock_redis.Redis.from_url.assert_called_once_with(
            "redis://localhost:6379/0"
        )
        self.assertIsNotNone(events.redis_client)

    def test_redis_client_initialization_with_rediss_url(self):
        """Test that redis client is initialized when db starts with rediss:// (SSL)"""
        events = self._create_events_with_redis("rediss://localhost:6379/0")

        self.mock_redis.Redis.from_url.assert_called_once_with(
            "rediss://localhost:6379/0"
        )
        self.assertIsNotNone(events.redis_client)

    def test_redis_client_not_initialized_with_file_path(self):
        """Test that redis client is not initialized when db is a file path"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        with patch("flower.events.redis", self.mock_redis):
            with patch("flower.events.shelve.open"):
                events = Events(self.capp, self.io_loop, db=db_path, persistent=True)

                self.mock_redis.Redis.from_url.assert_not_called()
                self.assertIsNone(events.redis_client)

    def test_redis_client_not_initialized_when_not_persistent(self):
        """Test that redis client is not initialized when persistent is False"""
        with patch("flower.events.redis", self.mock_redis):
            events = Events(
                self.capp, self.io_loop, db="redis://localhost:6379/0", persistent=False
            )

            self.mock_redis.Redis.from_url.assert_not_called()
            self.assertIsNone(events.redis_client)

    def test_redis_client_not_initialized_when_db_is_none(self):
        """Test that redis client is not initialized when db is None"""
        with patch("flower.events.redis", self.mock_redis), patch(
            "flower.events.shelve", self.mock_shelve
        ):
            events = Events(self.capp, self.io_loop, db=None, persistent=True)

            self.mock_redis.Redis.from_url.assert_not_called()
            self.assertIsNone(events.redis_client)

    def test_import_error_when_redis_not_available(self):
        """Test that ImportError is raised when redis is not installed"""
        with patch("flower.events.redis", None):
            with self.assertRaises(ImportError) as context:
                Events(
                    self.capp,
                    self.io_loop,
                    db="redis://localhost:6379/0",
                    persistent=True,
                )

            self.assertEqual(str(context.exception), "redis library is required")

    def test_load_state_from_redis(self):
        """Test loading state from Redis on initialization"""
        mock_state = EventsState()
        mock_state.counter = {"worker1": {"task-received": 5}}
        serialized_state = pickle.dumps(mock_state)

        self.mock_redis_client.get.return_value = serialized_state

        with patch("flower.events.redis", self.mock_redis):
            with patch("flower.events.pickle.loads", return_value=mock_state):
                events = Events(
                    self.capp,
                    self.io_loop,
                    db="redis://localhost:6379/0",
                    persistent=True,
                )

                self.mock_redis_client.get.assert_called_once_with("flower_events")
                self.assertIsNotNone(events.state)
                self.assertEqual(events.state.counter, mock_state.counter)

    def test_load_state_from_redis_when_empty(self):
        """Test that new state is created when Redis returns None"""
        events = self._create_events_with_redis()

        self.mock_redis_client.get.assert_called_once_with("flower_events")
        self.assertIsNotNone(events.state)
        self.assertIsInstance(events.state, EventsState)

    def test_save_state_to_redis(self):
        """Test saving state to Redis"""
        events = self._create_events_with_redis()

        # Modify state
        events.state.counter = {"worker1": {"task-received": 10}}

        with patch("flower.events.pickle.dumps") as mock_dumps:
            mock_dumps.return_value = b"serialized_data"
            events.save_state()

            # Verify pickle.dumps was called with state
            mock_dumps.assert_called_once_with(events.state)

            # Verify redis set was called
            self.mock_redis_client.set.assert_called_once()
            call_args = self.mock_redis_client.set.call_args
            self.assertEqual(call_args[0][0], "flower_events")
            self.assertEqual(call_args[0][1], b"serialized_data")

    def test_save_state_to_shelve_when_no_redis_client(self):
        """Test that state is saved to shelve when redis_client is None"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        with patch("flower.events.shelve", self.mock_shelve):
            events = Events(self.capp, self.io_loop, db=db_path, persistent=True)

            # Reset mocks after initialization
            self.mock_shelve.open.reset_mock()
            self.mock_shelve_db.__setitem__.reset_mock()
            self.mock_shelve_db.close.reset_mock()

            # Modify state
            events.state.counter = {"worker1": {"task-received": 10}}

            events.save_state()

            # Verify shelve was used
            self.mock_shelve.open.assert_called_once_with(db_path, flag="n")
            self.mock_shelve_db.__setitem__.assert_called_once_with(
                "events", events.state
            )
            self.mock_shelve_db.close.assert_called_once()

    def test_load_state_from_shelve_when_no_redis_client(self):
        """Test loading state from shelve when redis is not used"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            db_path = tmp.name

        # Create mock state in shelve
        mock_state = EventsState()
        mock_state.counter = {"worker1": {"task-received": 15}}
        self.mock_shelve_db.__getitem__.return_value = mock_state
        self.mock_shelve_db.__bool__.return_value = True

        events = self._create_events_with_shelve(db_path)

        # Verify state was loaded from shelve
        self.mock_shelve.open.assert_called()
        self.assertEqual(events.state.counter, mock_state.counter)

    def test_state_save_timer_initialized_with_interval(self):
        """Test that state save timer is initialized when state_save_interval is provided"""
        with patch("flower.events.redis", self.mock_redis):
            with patch("flower.events.PeriodicCallback") as mock_periodic:
                events = Events(
                    self.capp,
                    self.io_loop,
                    db="redis://localhost:6379/0",
                    persistent=True,
                    state_save_interval=5000,
                )

                # Verify PeriodicCallback was created for state saving
                self.assertEqual(
                    mock_periodic.call_count, 2
                )  # One for events, one for state save
                self.assertIsNotNone(events.state_save_timer)

    def test_state_save_timer_not_initialized_without_interval(self):
        """Test that state save timer is not initialized when state_save_interval is 0"""
        events = self._create_events_with_redis(state_save_interval=0)
        self.assertIsNone(events.state_save_timer)

    def test_redis_url_variations(self):
        """Test various Redis URL formats are handled correctly"""
        test_urls = [
            "redis://localhost:6379/0",
            "redis://localhost:6379",
            "redis://user:password@localhost:6379/0",
            "redis://:password@localhost:6379/0",
            "rediss://localhost:6379/0",
            "rediss://user:password@localhost:6379/0",
        ]

        with patch("flower.events.redis", self.mock_redis):
            for url in test_urls:
                # Reset mock for each iteration
                self.mock_redis.Redis.from_url.reset_mock()

                events = Events(self.capp, self.io_loop, db=url, persistent=True)

                self.mock_redis.Redis.from_url.assert_called_once_with(url)
                self.assertIsNotNone(events.redis_client)

    def test_stop_saves_state_when_persistent(self):
        """Test that stop() saves state when persistent mode is enabled"""
        events = self._create_events_with_redis()

        # Reset mock to ignore initialization calls
        self.mock_redis_client.set.reset_mock()

        events.stop()

        # Verify state was saved
        self.mock_redis_client.set.assert_called_once()
