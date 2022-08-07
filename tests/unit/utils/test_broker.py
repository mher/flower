import unittest
from unittest.mock import MagicMock

from flower.utils import broker
from flower.utils.broker import RabbitMQ, Redis, RedisBase, RedisSocket, Broker, RedisSentinel


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
        self.assertEqual(10000, b.port)
        self.assertEqual('vhost', b.vhost)
        self.assertEqual('user', b.username)
        self.assertEqual('pass', b.password)

    def test_url_vhost_slash(self):
        b = RabbitMQ('amqp://user:pass@host:10000//', '')
        self.assertEqual('host', b.host)
        self.assertEqual(10000, b.port)
        self.assertEqual('/', b.vhost)
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

    def test_priority_steps(self):
        custom_steps = list(range(10))
        cases = [(RedisBase.DEFAULT_PRIORITY_STEPS, {}),
                 (custom_steps, {'priority_steps': custom_steps})]
        for expected, options in cases:
            b = Broker('redis://localhost:6379/0', broker_options=options)
            self.assertEqual(expected, b.priority_steps)

    def test_custom_sep(self):
        custom_sep = '.'
        cases = [(RedisBase.DEFAULT_SEP, {}),
                 (custom_sep, {'sep': custom_sep})]
        for expected, options in cases:
            b = Broker('redis://localhost:6379/0', broker_options=options)
            self.assertEqual(expected, b.sep)

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


class TestRedisSentinel(unittest.TestCase):
    def test_init(self):
        options = {'master_name': 'my_redis_master'}
        b = Broker('sentinel://localhost:26379/', broker_options=options)
        self.assertFalse(isinstance(b, RabbitMQ))
        self.assertTrue(isinstance(b, RedisSentinel))

    def test_priority_steps(self):
        custom_steps = list(range(10))
        cases = [(RedisBase.DEFAULT_PRIORITY_STEPS, {'master_name': 'my_redis_master'}),
                 (custom_steps, {'master_name': 'my_redis_master', 'priority_steps': custom_steps})]
        for expected, options in cases:
            b = Broker('sentinel://localhost:6379/0', broker_options=options)
            self.assertEqual(expected, b.priority_steps)

    def test_url(self):
        options = {'master_name': 'my_redis_master'}
        b = Broker('sentinel://foo:7777/9', broker_options=options)
        self.assertEqual('foo', b.host)
        self.assertEqual(7777, b.port)
        self.assertEqual(9, b.vhost)

    def test_url_defaults(self):
        options = {'master_name': 'my_redis_master'}
        b = Broker('sentinel://', broker_options=options)
        self.assertEqual('localhost', b.host)
        self.assertEqual(26379, b.port)
        self.assertEqual(0, b.vhost)
        self.assertIsNone(b.username)
        self.assertIsNone(b.password)

    def test_url_with_password(self):
        options = {'master_name': 'my_redis_master'}
        b = Broker('sentinel://:pass@host:4444/5', broker_options=options)
        self.assertEqual('host', b.host)
        self.assertEqual(4444, b.port)
        self.assertEqual(5, b.vhost)
        self.assertEqual('pass', b.password)


class TestRedisSsl(unittest.TestCase):

    BROKER_USE_SSL_OPTIONS = {
        'ssl_cert_reqs': 0,
        'ssl_certfile': '/path/to/ssl_cert_file',
        'ssl_keyfile': '/path/to/ssl_key_file',
    }

    def test_init_with_broker_use_ssl(self):
        b = Broker('rediss://localhost:6379/0', broker_use_ssl=self.BROKER_USE_SSL_OPTIONS)
        self.assertFalse(isinstance(b, RabbitMQ))
        self.assertTrue(isinstance(b, Redis))

    def test_init_without_broker_use_ssl(self):
        with self.assertRaises(ValueError):
            Broker('rediss://localhost:6379/0')

    def test_redis_client_args(self):
        b = Broker('rediss://:pass@host:4444/5', broker_use_ssl=self.BROKER_USE_SSL_OPTIONS)
        self.assertEqual('host', b.host)
        self.assertEqual(4444, b.port)
        self.assertEqual(5, b.vhost)
        self.assertEqual('pass', b.password)

        redis_client_args = b._get_redis_client_args()
        for ssl_key, ssl_val in self.BROKER_USE_SSL_OPTIONS.items():
            self.assertIn(ssl_key, redis_client_args)
            self.assertEqual(ssl_val, redis_client_args[ssl_key])


class TestRedisSocket(unittest.TestCase):
    def test_init(self):
        b = Broker('redis+socket:///path/to/socket')
        self.assertFalse(isinstance(b, RabbitMQ))
        self.assertTrue(isinstance(b, RedisSocket))

    def test_url(self):
        b = Broker('redis+socket:///path/to/socket')
        self.assertEqual(None, b.host)
        self.assertEqual(None, b.port)
        self.assertEqual('path/to/socket', b.vhost)


if __name__ == '__main__':
    unittest.main()
