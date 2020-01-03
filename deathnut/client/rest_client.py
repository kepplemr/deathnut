import redis

from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

logger = get_deathnut_logger(__name__)

class DeathnutRestClient(DeathnutClient):
    def __init__(self, service, resource, strict=True, enabled=True, redis_connection=None,
            redis_host='redis', redis_port=6379, redis_pw=None, redis_db=0):
        """
        Parameters
        ----------
        strict: bool
            If False, user 'Unauthenticated' 
            Note: this value is a default and can be overiden when calling client methods.
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything. 
            Note: this value is a default and can be overiden when calling client methods.
        *Other params defined in superclass.
        """
        self._strict = strict
        self._enabled = enabled
        self._base_client = super().__init__(service, resource, redis_connection, redis_host,
            redis_port, redis_pw, redis_db)

    def _check_enabled_and_strict(self, user, enabled, strict):
        if not enabled:
            logger.warn('Authorization is not enabled')
            return False
        if not strict and user == 'Unauthenticated':
            logger.warn('Strict auth checking disabled, granting access to unauthenticated user')
            return False
        return True

    def execute_if_authorized(self, user, resource_id, enabled, strict, dont_wait, func, *args, **kwargs):
        pass