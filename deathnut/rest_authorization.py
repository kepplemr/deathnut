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
        enabled: bool
            If True, authorization checks will run. If False, all users will have access to
            everything. 
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

# def my_decorator(func):
#     def wrapper():
#         print("Something is happening before the function is called.")
#         func()
#         print("Something is happening after the function is called.")
#     return wrapper

# def do_twice(func):
#     @functools.wraps(func)
#     def wrapper_do_twice(*args, **kwargs):
#         func(*args, **kwargs)
#         return func(*args, **kwargs)
#     return wrapper_do_twice

    def _check_if_auth_runnable(self, func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped

    @_check_if_auth_runnable
    def assigns_roles(self, roles=[]):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                user = self._get_user_from_jwt_header(request)

                val = func(*args, user=user, roles=roles, **kwargs)
                return val
            return wrapped
        return decorator
    
    def assign(self, resource_id, **kwargs):
        user = kwargs['user']
        roles = kwargs['roles']
        logger.info('Assigning role(s) {} to user <{}> for resource <{}>, id <{}>'.format(roles, user, self.resource, resource_id))
        for role in roles:
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