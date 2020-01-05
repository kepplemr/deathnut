import redis
from concurrent.futures import ThreadPoolExecutor
from flask import jsonify

from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

logger = get_deathnut_logger(__name__)

class DeathnutRestClient(DeathnutClient):
    def __init__(self, service, resource_type=None, failure_callback=None, strict=True, 
            enabled=True, redis_connection=None, redis_host='redis', redis_port=6379, redis_pw=None,
            redis_db=0):
        """
        Parameters
        ----------
        failure_callback: func
            Return when authorization fails.
        strict: bool
            If False, user 'Unauthenticated' 
            Note: this value is a default and can be overiden when calling client methods.
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything. 
            Note: this value is a default and can be overiden when calling client methods.
        *Other params defined in superclass.
        """
        if failure_callback:
            self._on_failure = failure_callback
        else:
            self._on_failure = self._failure_callback
        self._strict = strict
        self._enabled = enabled
        super(DeathnutRestClient, self).__init__(service, resource_type, redis_connection, redis_host, redis_port, redis_pw, redis_db)
    
    def get_strict(self):
        return self._strict
    
    def get_enabled(self):
        return self._enabled
    
    def _failure_callback(self):
        return {'message':'Failed'}, 401

    def _is_auth_required(self, user, enabled, strict):
        """ id this is true, do not return wrapped function"""
        if not enabled:
            logger.warn('Authorization is not enabled')
            return False
        if not strict and user == 'Unauthenticated':
            logger.warn('Strict auth checking disabled, granting access to unauthenticated user')
            return False
        return True

    def _is_authorized(self, user, role, resource_id):
        """user is authenticated and has access to resource"""
        return self.check_role(user, role, resource_id)
    
    def _is_authenticated(self, user):
        return user != 'Unauthenticated'        

    def _deathnut_checks_successful(self, user, func, *args, **kwargs):
        """adds deathnut_calling_user to kwargs"""
        kwargs.update(deathnut_calling_user=user, deathnut_user=user)
        return func(*args, **kwargs)
    
    def execute_if_authorized(self, user, role, resource_id, enabled, strict, dont_wait, func, *args, **kwargs):
        if not self._is_auth_required(user, enabled, strict):
            return func(*args, **kwargs)
        if dont_wait:
            with ThreadPoolExecutor() as ex:
                # TODO only one needs to be on another thread?
                # TODO what if assign used within here on GET
                fetched_result = ex.submit(func, *args, **kwargs)
                is_authorized = ex.submit(self._is_authorized, user, role, resource_id)
                if is_authorized.result():
                    return fetched_result.result()
                return self._on_failure()
        if self._is_authorized(user, role, resource_id):
            return self._deathnut_checks_successful(user, func, *args, **kwargs)
        return self._on_failure()
    
    def execute_if_authenticated(self, user, enabled, strict, func, *args, **kwargs):
        if not self._is_auth_required(user, enabled, strict):
            return func(*args, **kwargs)
        if self._is_authenticated(user):
            return self._deathnut_checks_successful(user, func, *args, **kwargs)
        return self._on_failure()