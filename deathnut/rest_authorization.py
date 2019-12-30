import base64
import functools
import json
import logging
import redis
import sys

from flask import request

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

class RestAuthorization:
    strict = True
    enabled = True

    def __init__(self, resource, strict=True, enabled=True):
        """
        Parameters
        ----------
        resource: str
            Name of REST resource being protected.
        strict: bool
            If True, all requests must possess valid credentials extracted from JWT token. If False,
            unauthenticated users will have access to all resources. Useful for supporting traffic 
            not originating from ESP (inside the VPC) as we transition.
            Note: this value is a default and can be overrideen endpoint-by-endpoint.
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything. 
            Note: this value is a default and can be overrideen endpoint-by-endpoint.
        """
        self.resource = resource
        self.strict = strict
        self.enabled = enabled
        self.client = redis.Redis(host="redis", port=6379)

    def _get_user_from_jwt_header(self, request):
        user = 'Unauthenticated'
        jwt_header = request.headers.get('X-Endpoint-Api-Userinfo', '')
        if jwt_header:
            user = json.loads(base64.b64decode(jwt_header))['email']
        return user
    
    def _check_enabled_and_strict(self, user, enabled, strict):
        if not enabled:
            logger.warn('Authorization is not enabled')
            return False
        if not strict and user == 'Unauthenticated':
            logger.warn('Strict auth checking disabled, granting access to unauthenticated user')
            return False
        return True

    def assigns_roles(self, roles=[], enabled=enabled, strict=strict):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                # request must be passed from here to not be outside flask req context.
                user = self._get_user_from_jwt_header(request)
                if not self._check_enabled_and_strict(user, enabled, strict):
                    return func(*args, **kwargs)
                return func(*args, user=user, roles=roles, **kwargs)
            return wrapped
        return decorator
    
    def assign(self, resource_id, **kwargs):
        user = kwargs.get('user', '')
        roles = kwargs.get('roles', None)
        for role in roles:
            logger.info('Assigning role {} to user <{}> for resource <{}>, id <{}>'.format(role, user, self.resource, resource_id))
            self.client.hset(user, role, resource_id)

    # TODO GET logic here
    # def requires_role(self, role):
    #     def decorator(func):
    #         @functools.wraps(func)
    #         def wrapped(*args, **kwargs):
    #             # can perform auth_o check, fetch asynchronously
    #             if request.method == 'GET':
    #                 _perform_async_get()
    #             else:

    #             user = 'Unauthenticated'
    #             jwt_header = request.headers.get('X-Endpoint-Api-Userinfo', '')
    #             if jwt_header:
    #                 user = json.loads(base64.b64decode(jwt_header))['email']
    #             val = func(*args, user=user, **kwargs)