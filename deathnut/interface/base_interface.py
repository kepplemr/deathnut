import functools
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor

from deathnut.client.deathnut_client import DeathnutClient
from deathnut.util.abstract_classes import ABC
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)

class BaseAuthorizationInterface(ABC):
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
        *Other params defined in DeathnutClient.
        """
        self._client = DeathnutClient(service, resource_type, **kwargs)
        self._enabled_default = enabled
        self._strict_default = strict

    @staticmethod
    @abstractmethod
    def get_auth_header(*args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def get_resource_id(id_identifier, *args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def get_dont_wait(*args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def get_body_response(ret, *args, **kwargs):
        pass

    @abstractmethod
    def create_auth_endpoint(self, name, requires_role, grants_role):
        pass

    def get_client(self):
        return self._client

    def get_redis_connection(self):
        return self._client.get_redis_connection()

    def _get_auth_arguments(self, jwt_header, **kwargs):
        enabled = kwargs.get("enabled", self._enabled_default)
        strict = kwargs.get("strict", self._strict_default)
        user = get_user_from_jwt_header(jwt_header)
        return user, enabled, strict

    def requires_role(self, role, id_identifier="id", **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                resource_id = self.get_resource_id(id_identifier, *args, **kwargs)
                jwt_header = self.get_auth_header(*args, **kwargs)
                user, enabled, strict = self._get_auth_arguments(jwt_header, **kwargs)
                # if request is a GET, fetch resource asynchronously and return if authorized.
                dont_wait = self.get_dont_wait(*args, **kwargs)
                return self._execute_if_authorized(user, role, resource_id, enabled, strict,
                    dont_wait, func, *args, **kwargs)
            return wrapped
        return decorator

    def authentication_required(self, assign=[], uid_field="id", **kwargs):
        """
        If enabled is False, does nothing.
        If enabled and not strict, does nothing when called by an unauthenticated user.
          assign/revoke calls within the endpoint will be logged and ignored.
        If enabled and strict, requires callers to be successfully authenticated.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                jwt_header = self.get_auth_header(*args, **kwargs)
                user, enabled, strict = self._get_auth_arguments(jwt_header, **kwargs)
                if assign:
                    ret = self._execute_if_authenticated(user, enabled, strict, func, *args, **kwargs)
                    resp = dict(self.get_body_response(ret, *args, **kwargs))
                    uid = resp.get(uid_field)
                    if not uid:
                        raise DeathnutException("UID field <%s> not found in response <%s>" % (uid_field, resp))
                    self.assign_roles(uid, assign, deathnut_user=user, **kwargs)
                    return ret
                else:
                    return self._execute_if_authenticated(user, enabled, strict, func, *args, **kwargs)
            return wrapped
        return decorator

    def fetch_accessible_for_user(self, role, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                limit = kwargs.get('limit', 500)
                jwt_header = self.get_auth_header(*args, **kwargs)
                user, enabled, strict = self._get_auth_arguments(jwt_header, **kwargs)
                deathnut_ids = self._client.get_resources(user, role, limit)
                return self._execute_if_authenticated(user, enabled, strict, func, *args,
                    deathnut_ids=deathnut_ids, **kwargs)
            return wrapped
        return decorator

    def _change_roles(self, action, roles, resource_id, **kwargs):
        user = kwargs.get('deathnut_user', 'Unauthenticated')
        if not self.is_authenticated(user):
            logger.warn("Unauthenticated user attempt to update roles")
            return
        if roles:
            for role in roles:
                action(user, role, resource_id)

    def assign_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._client.assign_role, roles, resource_id, **kwargs)

    def revoke_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._client.revoke_role, roles, resource_id, **kwargs)

    def _is_auth_required(self, user, enabled, strict):
        """if this is true, do not return wrapped function"""
        if not enabled:
            logger.warn("Authorization is not enabled")
            return False
        if not strict and user == "Unauthenticated":
            logger.warn("Strict auth checking disabled, granting access to unauthenticated user")
            return False
        return True

    def is_authorized(self, user, role, resource_id):
        """user is authenticated and has access to resource"""
        if not self.is_authenticated(user):
            return not self._strict_default
        return self._client.check_role(user, role, resource_id)

    def is_authenticated(self, user):
        return user != "Unauthenticated"


    def _execute_if_authorized(self, dn_user, dn_role, dn_rid, dn_enabled, dn_strict, dn_dont_wait,
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
            return self._execute(dn_func, *args, **kwargs)
        if dn_dont_wait:
            return self._execute_asynchronously(dn_func, dn_role, dn_rid, *args,
                                                deathnut_user=dn_user, **kwargs)
        if self.is_authorized(dn_user, dn_role, dn_rid):
            return self._execute(dn_func, *args, deathnut_user=dn_user, **kwargs)
        raise DeathnutException("Not authorized")


    @staticmethod
    def _execute(dn_func, *args, **kwargs):
        return dn_func(*args, **kwargs)


    def _execute_asynchronously(self, dn_func, dn_role, dn_rid, *args, **kwargs):
        dn_user = kwargs.get('deathnut_user', 'Unauthenticated')
        with ThreadPoolExecutor() as ex:
            # assigns should not occur on GET / will not succeed as we dont pass user info
            fetched_result = ex.submit(dn_func, *args, **kwargs)
            is_authorized = ex.submit(self.is_authorized, dn_user, dn_role, dn_rid)
            if is_authorized.result():
                return fetched_result.result()
            raise DeathnutException("Not authorized")


    def _execute_if_authenticated(self, dn_user, dn_enabled, dn_strict, dn_func, *args, **kwargs):
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
            return self._execute(dn_func, *args, **kwargs)
        if self.is_authenticated(dn_user):
            return self._execute(dn_func, *args, deathnut_user=dn_user, **kwargs)
        raise DeathnutException("No authentication provided")
