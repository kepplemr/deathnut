import base64
import functools
import json
import logging
import sys

from concurrent.futures import ThreadPoolExecutor
from flask import request, jsonify
from functools import partial

from deathnut.client.rest_client import DeathnutRestClient
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)

class FlaskAuthorization(object):
    """Base class containing flask-specific logic"""

    def __init__(self, service, resource_type=None, strict=True, enabled=True, redis_connection=None):
        self._dnr_client = DeathnutRestClient(service, resource_type, strict, enabled, redis_connection=redis_connection)

    def _get_auth_arguments(self, request, **kwargs):
        enabled = kwargs.get('enabled', self._dnr_client.get_enabled())
        strict = kwargs.get('strict', self._dnr_client.get_strict())
        user = get_user_from_jwt_header(request)
        return user, enabled, strict

    def requires_role(self, role, id_identifier='id', **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                resource_id = kwargs[id_identifier]
                user, enabled, strict = self._get_auth_arguments(request, **kwargs)
                # if request is a GET, fetch resource asynchronously and return if authorized.
                dont_wait = kwargs.get('dont_wait', request.method == 'GET')
                return self._dnr_client.execute_if_authorized(user, role, resource_id, enabled, strict, dont_wait, func, *args, **kwargs)
            return wrapped
        return decorator 
    
    def authentication_required(self):
        """
        If enabled is False, does nothing.
        If enabled and not strict, does nothing when called by an unauthenticated user.
          assign/revoke calls within the endpoint will be logged and ignored.
        If enabled and strict, requires callers to be successfully authenticated.
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                # request must be passed from here to not be outside flask req context.
                user, enabled, strict = self._get_auth_arguments(request, **kwargs)
                return self._dnr_client.execute_if_authenticated(user, enabled, strict, func, *args, **kwargs)
            return wrapped
        return decorator
    
    def assign_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._dnr_client.assign_role, roles, resource_id, **kwargs)
    
    def revoke_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._dnr_client.revoke_role, roles, resource_id, **kwargs)
    
    def _change_roles(self, action, roles, resource_id, **kwargs):
        if 'deathnut_calling_user' not in kwargs:
            logger.warn('Unauthenticated user attempt to update roles')
            return
        user = kwargs.get('deathnut_user', '')
        if roles:
            for role in roles:
                action(user, role, resource_id)