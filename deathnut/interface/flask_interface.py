import base64
import functools
import json
import logging
import sys

from concurrent.futures import ThreadPoolExecutor
from flask import request, jsonify

from deathnut.client.rest_client import DeathnutRestClient
from deathnut.util.jwt import get_user_from_jwt_header

class RestAuthorization:
    def __init__(self, service, resource, strict=True, enabled=True, redis_host='redis', 
            redis_port=6379, redis_pw=None, redis_db=0):
        self.dnr_client = DeathnutRestClient(service, resource, strict, enabled, redis_host, redis_port, redis_pw, redis_db)

    def _get_auth_arguments(self, request, **kwargs):
        enabled = kwargs.get('enabled', self.dnr_client.get_enabled())
        strict = kwargs.get('strict', self.dnr_client.get_strict())
        user = get_user_from_jwt_header(request)
        return user, enabled, strict

    # if strict=False, goes through but resource has no associated auth (unauthed could still get)
    # if strict=True, fails 
    def assigns_roles(self, roles=[], **kwargs):
        """does not require authorization, only authentication if enabled=strict=True"""
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                # request must be passed from here to not be outside flask req context.
                user, enabled, strict = self._get_auth_arguments(request, **kwargs)
                kwargs.update(user=user, roles=roles)
                return self.dnr_client.execute_if_authenticated(user, enabled, strict, func, *args, **kwargs)
            return wrapped
        return decorator
    
    def assign(self, resource_id, **kwargs):
        user = kwargs.get('user', '')
        roles = kwargs.get('roles', None)
        # Handle unauthenticated here -but how do we return status?
        if roles:
            for role in roles:
                logger.info('Assigning role <{}> to user <{}> for resource <{}>, id <{}>'.format(role, user, self.resource, resource_id))
                self.client.hset('{}:{}'.format(user, role), resource_id, 'set')

    def requires_role(self, role, id_identifier='id'):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                resource_id = kwargs[id_identifier]
                user, enabled, strict = self._get_auth_arguments(request, **kwargs)
                # if request is a GET, fetch resource asynchronously and return if authorized.
                dont_wait = request.method == 'GET'
                return self.dnr_client.execute_if_authorized(user, resource_id, enabled, strict, dont_wait, func, *args, **kwargs)
            return wrapped
        return decorator                