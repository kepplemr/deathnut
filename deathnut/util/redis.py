import redis

from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

logger = get_deathnut_logger(__name__)

def get_redis_connection(**kwargs):
    """
    Returns a redis.Redis connection after verifying the connection is working.

    If redis_connection kwargs is not passed, will attempt to create a connection from the 
    redis_host, redis_port, redis_pw, redis_db kwargs.

    Kwargs Parameters
    ----------
    redis_connection: redis.Redis or redis.Strictredis (deprecated)
        redis client class. Allows deathnut clients to inject their custom redis connection.
        Clients that do not wish to handle their own redis can provide [redis_host, redis_port,
        redis_pw, redis_str] and we will create a default connection for them. 
    redis_host: str
        Hostname of redis server 
        *Note: used only if redis_connection not provided
    redis_port: int
        Port number of redis instance
        *Note: used only if redis_connection not provided
    redis_pw: str
        Redis instance password
        *Note: used only if redis_connection not provided
    redis_db: int
        Redis database index
        *Note: used only if redis_connection not provided
    """
    if 'redis_connection' in kwargs:
        client = kwargs['redis_connection']
    else:
        redis_host = kwargs.get('redis_host', None)
        redis_port = kwargs.get('redis_port', None)
        redis_pw = kwargs.get('redis_pw', None)
        redis_db = kwargs.get('redis_db', None)
        if None in (redis_host, redis_port):
            raise DeathnutException('redis_host and redis_port kwargs must be provided if redis connection not passed')
        client = redis.Redis(host=redis_host, port=redis_port, password=redis_pw, db=redis_db)
    try:
        client.ping()
    except:
        logger.exception('Could not establish redis connection')
    return client