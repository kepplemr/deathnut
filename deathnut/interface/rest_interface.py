import base64
import functools
import json
import logging
import sys

from concurrent.futures import ThreadPoolExecutor
from flask import request, jsonify

from deathnut.client import DeathnutClient

class RestAuthorization:
    def __init__(self, service, resource, strict=True, enabled=True, redis_host='redis', 
            redis_port=6379, redis_pw=None, redis_db=0):
        self.dn_client = DeathnutClient(service, resource, strict, enabled, redis_host, redis_port, redis_pw, redis_db)

    def _get_user_from_jwt_header(self, request):
        user = 'Unauthenticated'
        jwt_header = request.headers.get('X-Endpoint-Api-Userinfo', '')
        if jwt_header:
            user = json.loads(base64.b64decode(jwt_header))['email']
        return user

    def _get_auth_arguments(self, request, **kwargs):
        enabled = kwargs.get('enabled', self.dn_client.get_enabled())
        strict = kwargs.get('strict', self.dn_client.get_strict())
        user = self._get_user_from_jwt_header(request)
        return user, enabled, strict

    def assigns_roles(self, roles=[], **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                # request must be passed from here to not be outside flask req context.
                user, enabled, strict = self._get_auth_arguments(request, **kwargs)
                # auth_o is disabled or strict is false and user is unauthenticated
                if not self._check_enabled_and_strict(user, enabled, strict):
                    return func(*args, **kwargs)
                if not self._check_auth(user):
                    return jsonify({'message':'Failed'}), 401
                return func(*args, user=user, roles=roles, **kwargs)
            return wrapped
        return decorator
    
    def assign(self, resource_id, **kwargs):
        user = kwargs.get('user', '')
        roles = kwargs.get('roles', None)
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
                return deathnut_client.execute_if_authorized(user, resource_id, enabled, strict, dont_wait, func, *args, **kwargs)


                if not self._check_enabled_and_strict(user, enabled, strict):
                    return func(*args, **kwargs)
                
    
                if not self._check_auth(user, role, resource_id):
                    return jsonify({'message':'Failed'}), 401
                return func(*args, user=user, **kwargs)
            return wrapped
        return decorator                