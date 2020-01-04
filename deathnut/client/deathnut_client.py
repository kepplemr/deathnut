import itertools
import redis

from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

logger = get_deathnut_logger(__name__)

class DeathnutClient(object):
    def __init__(self, service, resource_type, redis_connection=None, redis_host='redis', 
            redis_port=6379, redis_pw=None, redis_db=0):
        """
        Parameters
        ----------
        service: str
            Name of calling service. 
        resource_type: str
            Optional name of specific resource being protected, used in the event services have
            multiple resource types. 
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
        if resource_type:
            self._name = '{}_{}'.format(service, resource_type)
        else:
            self._name = service
        if redis_connection:
            self._client = redis_connection
        else:
            if None in (redis_host, redis_port):
                raise DeathnutException('redis_host and redis_port must be provided if redis connection not passed.')
            logger.warn('Custom redis connection not passed, will use standard at {}:{}'.format(redis_host, redis_port))
            self._client = redis.Redis(host=redis_host, port=redis_port, password=redis_pw, db=redis_db)
        self._client.ping()
    
    def assign_role(self, user, role, resource_id):
        self._client.hset('{}:{}:{}'.format(self._name, user, role), resource_id, 'T')

    def check_role(self, user, role, resource_id):
        return bool(self._client.hget('{}:{}:{}'.format(self._name, user,role), resource_id))
    
    def revoke_role(self, user, role, resource_id):
        self._client.hdel('{}:{}:{}'.format(self._name, user, role), resource_id)

    def get_resources(self, user, role, page_size=10):
        """redis default is a count of 10"""
        cursor = '0'
        while cursor != 0:
            cursor, data = self._client.hscan('{}:{}:{}'.format(self._name, user, role), cursor=cursor, count=page_size)
            yield [x[0].decode() for x in data.items()]

