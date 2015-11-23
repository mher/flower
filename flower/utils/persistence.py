import logging
import pickle
import shelve
import numbers

try:
    from urllib.parse import urlparse, urljoin, quote, unquote
except ImportError:
    from urlparse import urlparse, urljoin
    from urllib import quote, unquote

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

class PersistenceBase(object):
    def __init__(self, db):
        raise NotImplementedError()

    def save(self, key, value):
        raise NotImplementedError()

    def read(self, key):
        raise NotImplementedError()

class ShelvePersistence(PersistenceBase):
    def __init__(self, db):
        logger.info("Initializing ShelvePersistence.")
        self.db = db

    def save(self, key, value):
        logger.info("Saving with ShelvePersistence.")
        with shelve.open(self.db) as state:
            state[key] = value

    def read(self, key):
        logger.info("Saving with ShelvePersistence.")
        with shelve.open(self.db) as state:
            return state[key]

class RedisPersistence(PersistenceBase):
    PERSISTENCE_HASH = 'flower:persistence'
    def __init__(self, db):
        logger.info("Initializing RedisPersistence")
        if not redis:
            raise ImportError('redis library is required')

        purl = urlparse(db)
        host = purl.hostname or 'localhost'
        port = purl.port or 6379
        password = unquote(purl.password) if purl.password else purl.password
        vhost = self._prepare_virtual_host(purl.path[1:])

        self.redis = redis.Redis(host=host, port=port, db=vhost, password=password)

    def save(self, key, value):
        logger.info("Saving with RedisPersistence.")
        self.redis.hset(self.PERSISTENCE_HASH, key, pickle.dumps(value))

    def read(self, key):
        logger.info("Reading with RedisPersistence.")
        return pickle.loads(self.redis.hget(self.PERSISTENCE_HASH, key))

    def _prepare_virtual_host(self, vhost):
        if not isinstance(vhost, numbers.Integral):
            if not vhost or vhost == '/':
                vhost = 0
            elif vhost.startswith('/'):
                vhost = vhost[1:]
            try:
                vhost = int(vhost)
            except ValueError:
                raise ValueError(
                    'Database is int between 0 and limit - 1, not {0}'.format(
                        vhost,
                    ))
        return vhost

class Persistence(object):
    def __new__(cls, db):
        scheme = urlparse(db).scheme
        if scheme == 'redis':
            return RedisPersistence(db)
        return ShelvePersistence(db)

if __name__ == '__main__':
    r = Persistence('redis://')
    r.save('events', 'hello')
    print(r.read('events'))

    r = Persistence('db')
    r.save('events', 'hello')
    print(r.read('events'))
