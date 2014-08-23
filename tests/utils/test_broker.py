import unittest

from mock import MagicMock

from flower.utils import broker
from flower.utils.broker import RabbitMQ, Redis, Broker


# python 2.6 support
if not hasattr(unittest.TestCase, 'assertIn'):
    import unittest2 as unittest


broker.requests = MagicMock()
broker.redis = MagicMock()


class TestRabbitMQ(unittest.TestCase):
    def test_init(self):
        b = Broker('amqp://', '')
        self.assertTrue(isinstance(b, RabbitMQ))
        self.assertFalse(isinstance(b, Redis))

    def test_url(self):
        b = RabbitMQ('amqp://user:pass@host:10000/vhost', '')
        self.assertEqual('host', b.host)
        self.assertEqual(15672, b.port)
        self.assertEqual('vhost', b.vhost)
        self.assertEqual('user', b.username)
        self.assertEqual('pass', b.password)

    def test_url_defaults_rabbitmq(self):
        for url in ['amqp://', 'amqp://localhost']:
            b = RabbitMQ(url, '')
            self.assertEqual('localhost', b.host)
            self.assertEqual(15672, b.port)
            self.assertEqual('/', b.vhost)
            self.assertEqual('guest', b.username)
            self.assertEqual('guest', b.password)

    def test_url_defaults_redis(self):
        for url in ['redis://', 'redis://localhost', 'redis://localhost/0']:
            b = Redis(url, '')
            self.assertEqual('localhost', b.host)
            self.assertEqual(6379, b.port)
            self.assertEqual(0, b.vhost)
            self.assertEqual(None, b.username)
            self.assertEqual(None, b.password)


class TestRedis(unittest.TestCase):
    def test_init(self):
        b = Broker('redis://localhost:6379/0')
        self.assertFalse(isinstance(b, RabbitMQ))
        self.assertTrue(isinstance(b, Redis))

    def test_url(self):
        b = Broker('redis://foo:7777/9')
        self.assertEqual('foo', b.host)
        self.assertEqual(7777, b.port)
        self.assertEqual(9, b.vhost)

    def test_url_defaults(self):
        b = Broker('redis://')
        self.assertEqual('localhost', b.host)
        self.assertEqual(6379, b.port)
        self.assertEqual(0, b.vhost)
        self.assertIsNone(b.username)
        self.assertIsNone(b.password)

    def test_url_with_password(self):
        b = Broker('redis://:pass@host:4444/5')
        self.assertEqual('host', b.host)
        self.assertEqual(4444, b.port)
        self.assertEqual(5, b.vhost)
        self.assertEqual('pass', b.password)


if __name__ == '__main__':
    unittest.main()
