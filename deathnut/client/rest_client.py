import redis
from concurrent.futures import ThreadPoolExecutor
from flask import jsonify

from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

logger = get_deathnut_logger(__name__)

class DeathnutRestClient(DeathnutClient):
    def __init__(self, service, resource_type=None, strict=True, enabled=True, **kwargs):
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
        super(DeathnutRestClient, self).__init__(service, resource_type, **kwargs)
    
    def get_strict(self):
        return self._strict
    
    def get_enabled(self):
        return self._enabled

    def _is_auth_required(self, user, enabled, strict):
        """if this is true, do not return wrapped function"""
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

    def _deathnut_checks_successful(self, dn_user, dn_func, *args, **kwargs):
        """adds deathnut_calling_user to kwargs"""
        logger.warn("Kwargs before -> " + str(kwargs))
        kwargs.update(deathnut_calling_user=dn_user, deathnut_user=dn_user)
        logger.warn("Kwargs after -> " + str(kwargs))
        return dn_func(*args, **kwargs)
    
    def execute_if_authorized(self, dn_user, dn_role, dn_rid, dn_enabled, dn_strict, dn_dont_wait, 
        dn_func, *args, **kwargs):
        """
        Executes a wrapped function if a user has the required role for a given resource_id.

        Note: args for wrapped function are passed in args, kwargs. Wrapped functions should not use
        dn_* vars.

        Parameters
        ----------
        dn_user: str
            The user seeking access.
        dn_role: str
            The role needed to access the resource id.
        dn_rid: str
            The resource id being sought.
        dn_enabled: bool
            Whether deathnut is enabled.
        dn_strict: bool
            Whether deathnut, if enabled, will allow access to unauthenticated users.
        dn_func: function
            The wrapped function.
        """
        if not self._is_auth_required(dn_user, dn_enabled, dn_strict):
            return dn_func(*args, **kwargs)
        if dn_dont_wait:
            with ThreadPoolExecutor() as ex:
                # TODO what if assign used within here on GET
                fetched_result = ex.submit(dn_func, *args, **kwargs)
                is_authorized = ex.submit(self._is_authorized, dn_user, dn_role, dn_rid)
                if is_authorized.result():
                    return fetched_result.result()
                raise DeathnutException('Not authorized')
        if self._is_authorized(dn_user, dn_role, dn_rid):
            return self._deathnut_checks_successful(dn_user, dn_func, *args, **kwargs)
        raise DeathnutException('Not authorized')
    
    def execute_if_authenticated(self, dn_user, dn_enabled, dn_strict, dn_func, *args, **kwargs):
        """
        Executes a wrapped function if a user is authenticated (not authorization checks).

        Note: args for wrapped function are passed in args, kwargs. Wrapped functions should not use
        dn_* vars.

        Parameters
        ----------
        dn_user: str
            The username seeking access to function. This will be 'unauthenticated' if no auth
            was performed.
        dn_enabled: bool
            Whether deathnut is enabled.
        dn_strict: bool
            Whether deathnut, if enabled, will allow access to unauthenticated users.
        dn_func: function
            The wrapped function.
        """
        if not self._is_auth_required(dn_user, dn_enabled, dn_strict):
            return dn_func(*args, **kwargs)
        if self._is_authenticated(dn_user):
            return self._deathnut_checks_successful(dn_user, dn_func, *args, **kwargs)
        raise DeathnutException('No authentication provided')