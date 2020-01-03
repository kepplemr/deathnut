
import redis

from util import DeathnutException, get_deathnut_logger

logger = get_deathnut_logger(__name__)

class DeathnutClient:
    def __init__(self, service, resource, strict=True, enabled=True, redis_connection=None,
            redis_host='redis', redis_port=6379, redis_pw=None, redis_db=0):
        """
        Parameters
        ----------
        service: str
            Name of calling service. 
        resource: str
            Name of REST resource being protected.
        failure_callback: func
            Return when authorization fails.
        strict: bool
            If False, user 'Unauthenticated' 
            Note: this value is a default and can be overiden when calling client methods.
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything. 
            Note: this value is a default and can be overiden when calling client methods.
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
        self._service = service
        self._resource = resource
        self._strict = strict
        self._enabled = enabled
        if redis_connection:
            self._client = redis_connection
        else:
            if None in (redis_host, redis_port):
                raise DeathnutException('redis_host and redis_port must be provided if redis connection not passed.')
            logger.warn('Custom redis connection not passed, will use standard at {}:{}'.format(redis_host, redis_port))
            self._client = redis.Redis(host=redis_host, port=redis_port, password=redis_pw, db=redis_db)
        self._client.ping()

    def _check_enabled_and_strict(self, user, enabled, strict):
        if not enabled:
            logger.warn('Authorization is not enabled')
            return False
        if not strict and user == 'Unauthenticated':
            logger.warn('Strict auth checking disabled, granting access to unauthenticated user')
            return False
        return True

    def _check_auth(self, user, role=None, resource_id=None):
        if user == 'Unauthenticated':
            return False
        if resource_id:
            return self._client.hget('{}:{}'.format(user,role), resource_id)
        return True
    
    def assign_role(self, user, role, resource_id):
        if user == 'Unauthenticated':
            logger.error('Unauthenticated users cannot be assigned roles')
            return False

    def check_role(self, user, role, resource_id):
        pass
        #if self._check_auth(user, enabled, strict)



# Have a child RestClient
    def execute_if_authorized(self, user, resource_id, enabled, strict, dont_wait, func, *args, **kwargs):
        pass