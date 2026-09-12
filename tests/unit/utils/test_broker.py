import ssl
import unittest
from typing import ClassVar
from unittest import mock

from flower.utils import broker
from flower.utils.broker import (
    Broker,
    RabbitMQ,
    Redis,
    RedisBase,
    RedisSentinel,
    RedisSocket,
    RedisSsl,
    validate_broker_api,
)


class TestRabbitMQ(unittest.TestCase):
    def test_init(self):
        for url in ['amqp://', 'amqps://']:
            b = Broker(url, '')
            self.assertTrue(isinstance(b, RabbitMQ))
            self.assertFalse(isinstance(b, Redis))

    def test_url(self):
        b = RabbitMQ('amqp://user:pass@host:10000/vhost', '')
        self.assertEqual('host', b.host)
        self.assertEqual(15672, b.port)
        self.assertEqual('vhost', b.vhost)
        self.assertEqual('user', b.username)
        self.assertEqual('pass', b.password)

    def test_url_vhost_slash(self):
        b = RabbitMQ('amqp://user:pass@host:10000//', '')
        self.assertEqual('host', b.host)
        self.assertEqual(15672, b.port)
        self.assertEqual('/', b.vhost)
        self.assertEqual('user', b.username)
        self.assertEqual('pass', b.password)

    def test_url_defaults_rabbitmq(self):
        for url in ['amqp://', 'amqp://localhost', 'amqps://', 'amqps://localhost']:
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

    def test_http_api_ignores_amqp_port(self):
        b = RabbitMQ('amqp://user:pass@host:5672/vhost', None)
        self.assertEqual('http://user:pass@host:15672/api/vhost', b.http_api)

    def test_invalid_http_api(self):
        for http_api in ['ftp://guest:guest@host:15672/api/', 'http://']:
            with self.assertRaises(ValueError):
                validate_broker_api(http_api)

    def test_valid_http_api(self):
        for http_api in ['http://guest:guest@host:15672/api/',
                         'https://rabbit.internal:15671/api/']:
            validate_broker_api(http_api)

    def test_invalid_http_api_does_not_leak_password(self):
        with self.assertRaises(ValueError) as cm:
            validate_broker_api('ftp://guest:s3cr3t@host:15672/api/')
        self.assertNotIn('s3cr3t', str(cm.exception))

    def test_verifies_cert_by_default(self):
        b = RabbitMQ('amqps://user:pass@host:15672/vhost', '')
        self.assertEqual({'validate_cert': True}, b._tls_kwargs())

    def test_honors_broker_use_ssl_ca_certs(self):
        b = RabbitMQ('amqps://user:pass@host:15672/vhost', '',
                     broker_use_ssl={'ssl_ca_certs': '/etc/ca.pem'})
        self.assertEqual(
            {'validate_cert': True, 'ca_certs': '/etc/ca.pem'}, b._tls_kwargs())

    def test_broker_use_ssl_cert_none_disables_verification(self):
        b = RabbitMQ('amqps://user:pass@host:15672/vhost', '',
                     broker_use_ssl={'ssl_cert_reqs': ssl.CERT_NONE,
                                     'ssl_ca_certs': '/etc/ca.pem'})
        self.assertEqual({'validate_cert': False}, b._tls_kwargs())


class TestRedis(unittest.TestCase):
    def test_invalid_database_error_message(self):
        with self.assertRaises(ValueError) as cm:
            Broker('redis://localhost:6379/notanint')
        self.assertIn('notanint', str(cm.exception))

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

    def test_client_timeouts(self):
        b = Broker('redis://localhost:6379/0')
        args = b._get_redis_client_args()
        self.assertEqual(1.0, args['socket_connect_timeout'])
        self.assertEqual(2.0, args['socket_timeout'])
        self.assertEqual(0, args['retry'].get_retries())

    def test_client_options(self):
        options = {
            'socket_connect_timeout': 3.0,
            'socket_timeout': 4.0,
            'visibility_timeout': 6,
        }
        b = Broker('redis://localhost:6379/0', broker_options=options)
        args = b._get_redis_client_args()
        self.assertEqual(3.0, args['socket_connect_timeout'])
        self.assertEqual(4.0, args['socket_timeout'])
        self.assertNotIn('visibility_timeout', args)

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

    def test_url_with_user_and_password(self):
        b = Broker('redis://user:pass@host:4444/5')
        self.assertEqual('host', b.host)
        self.assertEqual(4444, b.port)
        self.assertEqual(5, b.vhost)
        self.assertEqual('user', b.username)
        self.assertEqual('pass', b.password)

    def test_ipv6(self):
        b = Broker('redis://[::1]')
        self.assertEqual('::1', b.host)
        self.assertEqual(6379, b.port)
        self.assertEqual(0, b.vhost)

    def test_url_encoded_ipv6(self):
        b = Broker('redis://2001%3Adb8%3A%3A1:6379/3')
        self.assertEqual('2001:db8::1', b.host)
        self.assertEqual(6379, b.port)
        self.assertEqual(3, b.vhost)


class TestRedisQueues(unittest.IsolatedAsyncioTestCase):
    async def test_queues_uses_async_pipeline(self):
        class Pipeline:
            def __init__(self):
                self.keys = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            def llen(self, key):
                self.keys.append(key)

            async def execute(self):
                return range(1, len(self.keys) + 1)

        class Client:
            def __init__(self):
                self.pipeline_instance = Pipeline()
                self.closed = False

            def pipeline(self):
                return self.pipeline_instance

            async def aclose(self):
                self.closed = True

        b = Broker('redis://localhost:6379/0')
        client = Client()
        b.redis = client

        queues = await b.queues(['celery', 'priority'])

        self.assertEqual([
            {'name': 'celery', 'messages': 10},
            {'name': 'priority', 'messages': 26},
        ], queues)
        self.assertEqual([
            'celery',
            'celery\x06\x163',
            'celery\x06\x166',
            'celery\x06\x169',
            'priority',
            'priority\x06\x163',
            'priority\x06\x166',
            'priority\x06\x169',
        ], client.pipeline_instance.keys)
        self.assertTrue(client.closed)


class TestRedisSentinel(unittest.TestCase):
    def test_invalid_database_error_message(self):
        options = {'master_name': 'my_redis_master'}
        with self.assertRaises(ValueError) as cm:
            Broker('sentinel://localhost:26379/notanint', broker_options=options)
        self.assertIn('notanint', str(cm.exception))

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

    def test_master_client_authenticates_with_url_user(self):
        options = {'master_name': 'my_redis_master'}
        with mock.patch.object(broker.redis.sentinel, 'Sentinel') as sentinel:
            Broker('sentinel://app:secret@host:26379/0', broker_options=options)
        kwargs = sentinel.call_args.kwargs
        self.assertEqual('app', kwargs['username'])
        self.assertEqual('secret', kwargs['password'])

    def test_master_client_without_user_in_url(self):
        options = {'master_name': 'my_redis_master'}
        with mock.patch.object(broker.redis.sentinel, 'Sentinel') as sentinel:
            Broker('sentinel://:secret@host:26379/0', broker_options=options)
        self.assertFalse(sentinel.call_args.kwargs['username'])


class TestRedisSsl(unittest.TestCase):

    BROKER_USE_SSL_OPTIONS: ClassVar[dict] = {
        'ssl_cert_reqs': 0,
        'ssl_certfile': '/path/to/ssl_cert_file',
        'ssl_keyfile': '/path/to/ssl_key_file',
    }

    def test_init_with_broker_use_ssl(self):
        b = Broker('rediss://localhost:6379/0', broker_use_ssl=self.BROKER_USE_SSL_OPTIONS)
        self.assertFalse(isinstance(b, RabbitMQ))
        self.assertTrue(isinstance(b, Redis))

    def test_init_with_redis_scheme_and_broker_use_ssl(self):
        b = Broker('redis://localhost:6379/0', broker_use_ssl=self.BROKER_USE_SSL_OPTIONS)
        self.assertIsInstance(b, RedisSsl)

        redis_client_args = b._get_redis_client_args()
        self.assertTrue(redis_client_args['ssl'])
        for ssl_key, ssl_val in self.BROKER_USE_SSL_OPTIONS.items():
            self.assertEqual(ssl_val, redis_client_args[ssl_key])

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
