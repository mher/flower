import asyncio
import json
import logging
import numbers
import socket
import sys
from urllib.parse import quote, unquote, urljoin, urlparse

from tornado import httpclient, ioloop

try:
    import redis
except ImportError:
    redis = None


logger = logging.getLogger(__name__)


class BrokerBase:
    def __init__(self, broker_url, *_, **__):
        purl = urlparse(broker_url)
        self.host = purl.hostname
        self.port = purl.port
        self.vhost = purl.path[1:]

        username = purl.username
        password = purl.password

        self.username = unquote(username) if username else username
        self.password = unquote(password) if password else password

    async def queues(self, names):
        raise NotImplementedError


class RabbitMQ(BrokerBase):
    def __init__(self, broker_url, http_api, io_loop=None, **__):
        super().__init__(broker_url)
        self.io_loop = io_loop or ioloop.IOLoop.instance()

        self.host = self.host or 'localhost'
        self.port = self.port or 15672
        self.vhost = quote(self.vhost, '') or '/' if self.vhost != '/' else self.vhost
        self.username = self.username or 'guest'
        self.password = self.password or 'guest'

        if not http_api:
            http_api = f"http://{self.username}:{self.password}@{self.host}:{self.port}/api/{self.vhost}"

        try:
            self.validate_http_api(http_api)
        except ValueError:
            logger.error("Invalid broker api url: %s", http_api)

        self.http_api = http_api

    async def queues(self, names):
        url = urljoin(self.http_api, 'queues/' + self.vhost)
        api_url = urlparse(self.http_api)
        username = unquote(api_url.username or '') or self.username
        password = unquote(api_url.password or '') or self.password

        http_client = httpclient.AsyncHTTPClient()
        try:
            response = await http_client.fetch(
                url, auth_username=username, auth_password=password,
                connect_timeout=5.0, request_timeout=30.0,
                validate_cert=False)
        except (socket.error, httpclient.HTTPError) as e:
            logger.error("RabbitMQ management API call failed: %s", e)
            return []

        if response.code == 200:
            info = json.loads(response.body.decode())
            names_set = frozenset(names)
            return [x for x in info if x['name'] in names_set]
        response.rethrow()
        return []

    @classmethod
    def validate_http_api(cls, http_api):
        url = urlparse(http_api)
        if url.scheme not in ('http', 'https'):
            raise ValueError(f"Invalid http api schema: {url.scheme}")


class RedisBase(BrokerBase):
    DEFAULT_SEP = '\x06\x16'
    DEFAULT_PRIORITY_STEPS = [0, 3, 6, 9]

    def __init__(self, broker_url, *_, **kwargs):
        super().__init__(broker_url)
        self.redis = None

        if not redis:
            raise ImportError('redis library is required')

        broker_options = kwargs.get('broker_options', {})
        self.priority_steps = broker_options.get(
            'priority_steps', self.DEFAULT_PRIORITY_STEPS)
        self.sep = broker_options.get('sep', self.DEFAULT_SEP)
        self.broker_prefix = broker_options.get('global_keyprefix', '')

    def close(self):
        """Close the Redis connection and release resources."""
        if self.redis is not None:
            try:
                if hasattr(self.redis, 'close'):
                    self.redis.close()
                elif hasattr(self.redis, 'connection_pool'):
                    self.redis.connection_pool.disconnect()
            except Exception:
                logger.debug("Error closing Redis connection", exc_info=True)
            self.redis = None

    def _q_for_pri(self, queue, pri):
        if pri not in self.priority_steps:
            raise ValueError('Priority not in priority steps')
        # pylint: disable=consider-using-f-string
        return '{0}{1}{2}'.format(*((queue, self.sep, pri) if pri else (queue, '', '')))

    _PIPELINE_CHUNK_SIZE = 5000

    async def queues(self, names):
        if not names:
            return []

        steps = len(self.priority_steps)

        # Build all Redis key names upfront
        all_keys = []
        for name in names:
            for pri in self.priority_steps:
                all_keys.append(self.broker_prefix + self._q_for_pri(name, pri))

        # Execute pipelined LLEN in chunks to avoid overwhelming Redis
        # with a single huge pipeline for very large queue counts.
        all_results = []
        chunk_size = self._PIPELINE_CHUNK_SIZE
        for start in range(0, len(all_keys), chunk_size):
            pipe = self.redis.pipeline(transaction=False)
            for key in all_keys[start:start + chunk_size]:
                pipe.llen(key)
            all_results.extend(pipe.execute())

        queue_stats = []
        for i, name in enumerate(names):
            offset = i * steps
            total = sum(all_results[offset:offset + steps])
            queue_stats.append({'name': name, 'messages': total})
        return queue_stats


class Redis(RedisBase):

    def __init__(self, broker_url, *args, **kwargs):
        super().__init__(broker_url, *args, **kwargs)
        self.host = self.host or 'localhost'
        self.port = self.port or 6379
        self.vhost = self._prepare_virtual_host(self.vhost)
        self.redis = self._get_redis_client()

    def _prepare_virtual_host(self, vhost):
        if not isinstance(vhost, numbers.Integral):
            if not vhost or vhost == '/':
                vhost = 0
            elif vhost.startswith('/'):
                vhost = vhost[1:]
            try:
                vhost = int(vhost)
            except ValueError as exc:
                raise ValueError(f'Database is int between 0 and limit - 1, not {vhost}') from exc
        return vhost

    def _get_redis_client_args(self):
        return {
            'host': self.host,
            'port': self.port,
            'db': self.vhost,
            'username': self.username,
            'password': self.password
        }

    def _get_redis_client(self):
        return redis.Redis(**self._get_redis_client_args())


class RedisSentinel(RedisBase):

    def __init__(self, broker_url, *args, **kwargs):
        super().__init__(broker_url, *args, **kwargs)
        broker_options = kwargs.get('broker_options', {})
        broker_use_ssl = kwargs.get('broker_use_ssl', None)
        self.host = self.host or 'localhost'
        self.port = self.port or 26379
        self.vhost = self._prepare_virtual_host(self.vhost)
        self.master_name = self._prepare_master_name(broker_options)
        self.redis = self._get_redis_client(broker_options, broker_use_ssl)

    def _prepare_virtual_host(self, vhost):
        if not isinstance(vhost, numbers.Integral):
            if not vhost or vhost == '/':
                vhost = 0
            elif vhost.startswith('/'):
                vhost = vhost[1:]
            try:
                vhost = int(vhost)
            except ValueError as exc:
                raise ValueError('Database is int between 0 and limit - 1, not {vhost}') from exc
        return vhost

    def _prepare_master_name(self, broker_options):
        try:
            master_name = broker_options['master_name']
        except KeyError as exc:
            raise ValueError('master_name is required for Sentinel broker') from exc
        return master_name

    def _get_redis_client(self, broker_options, broker_use_ssl):
        connection_kwargs = {
            'password': self.password,
            'sentinel_kwargs': broker_options.get('sentinel_kwargs')
        }
        if isinstance(broker_use_ssl, dict):
            connection_kwargs['ssl'] = True
            connection_kwargs.update(broker_use_ssl)
        # get all sentinel hosts from Celery App config and use them to initialize Sentinel
        sentinel = redis.sentinel.Sentinel(
            [(self.host, self.port)], **connection_kwargs)
        redis_client = sentinel.master_for(self.master_name)
        return redis_client


class RedisSocket(RedisBase):

    def __init__(self, broker_url, *args, **kwargs):
        super().__init__(broker_url, *args, **kwargs)
        self.redis = redis.Redis(unix_socket_path='/' + self.vhost,
                                 password=self.password)


class RedisSsl(Redis):
    """
    Redis SSL class offering connection to the broker over SSL.
    This does not currently support SSL settings through the url, only through
    the broker_use_ssl celery configuration.
    """

    def __init__(self, broker_url, *args, **kwargs):
        if 'broker_use_ssl' not in kwargs:
            raise ValueError('rediss broker requires broker_use_ssl')
        self.broker_use_ssl = kwargs.get('broker_use_ssl', {})
        super().__init__(broker_url, *args, **kwargs)

    def _get_redis_client_args(self):
        client_args = super()._get_redis_client_args()
        client_args['ssl'] = True
        if isinstance(self.broker_use_ssl, dict):
            client_args.update(self.broker_use_ssl)
        return client_args


class Broker:
    """Factory returning the appropriate broker client based on URL scheme.

    Supported schemes:
    ``amqp`` or ``amqps``  -> :class:`RabbitMQ`
    ``redis``              -> :class:`Redis`
    ``rediss``             -> :class:`RedisSsl`
    ``redis+socket``       -> :class:`RedisSocket`
    ``sentinel``           -> :class:`RedisSentinel`
    """

    def __new__(cls, broker_url, *args, **kwargs):
        scheme = urlparse(broker_url).scheme
        if scheme in ('amqp', 'amqps'):
            return RabbitMQ(broker_url, *args, **kwargs)
        if scheme == 'redis':
            return Redis(broker_url, *args, **kwargs)
        if scheme == 'rediss':
            return RedisSsl(broker_url, *args, **kwargs)
        if scheme == 'redis+socket':
            return RedisSocket(broker_url, *args, **kwargs)
        if scheme == 'sentinel':
            return RedisSentinel(broker_url, *args, **kwargs)
        raise NotImplementedError

    async def queues(self, names):
        raise NotImplementedError


async def main():
    broker_url = sys.argv[1] if len(sys.argv) > 1 else 'amqp://'
    queue_name = sys.argv[2] if len(sys.argv) > 2 else 'celery'
    if len(sys.argv) > 3:
        http_api = sys.argv[3]
    else:
        http_api = 'http://guest:guest@localhost:15672/api/'

    broker = Broker(broker_url, http_api=http_api)
    queues = await broker.queues([queue_name])
    if queues:
        print(queues)


if __name__ == "__main__":
    asyncio.run(main())
