import base64
import functools
import json
import logging
import sys

from concurrent.futures import ThreadPoolExecutor
#from flask import request, jsonify
from functools import partial

from deathnut.client.rest_client import DeathnutRestClient
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

import falcon
from apispec import APISpec

logger = get_deathnut_logger(__name__)

class ErrorHandler:
    @staticmethod
    def deathnut_exception(ex, req, resp, params):
        resp.media = {'message': ex.args[0]}
        resp.status = falcon.HTTP_401

class FalconAuthorization(object):
    """Base class containing flask-specific logic"""

    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, redis_connection=None):
        self._app = app
        self._dnr_client = DeathnutRestClient(service, resource_type, strict, enabled, redis_connection=redis_connection)
        self._app.add_error_handler(DeathnutException, ErrorHandler.deathnut_exception)
        self._enabled_default = self._dnr_client.get_enabled()
        self._strict_default = self._dnr_client.get_strict()
    
    @staticmethod
    def get_auth_header(*args, **kwargs):
        req = args[1]
        return req.get_header('X-Endpoint-Api-Userinfo', default='')

    @staticmethod
    def get_auth_arguments(jwt_header, enabled_default, strict_default, **kwargs):
        enabled = kwargs.get('enabled', enabled_default)
        strict = kwargs.get('strict', strict_default)
        user = get_user_from_jwt_header(jwt_header)
        return user, enabled, strict

    def requires_role(self, role, id_identifier='id', **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                dn_args = request.view_args
                if request.json:
                    dn_args.update(request.json)
                #resource_id = kwargs[id_identifier]
                #args = getattr(request, 'json', {}).update(request.view_args)
                #args = request.json.update(request.views_args)
                # for attr in dir(request):
                #     logger.warn('{} : {}'.format(attr, getattr(request, attr)))
                resource_id = dn_args[id_identifier]
                #resource_id = 'asdasdas'
                user, enabled, strict = self._get_auth_arguments(request, True, False, **kwargs)
                # if request is a GET, fetch resource asynchronously and return if authorized.
                dont_wait = kwargs.get('dont_wait', request.method == 'GET')
                return self._dnr_client.execute_if_authorized(user, role, resource_id, enabled, strict, dont_wait, func, *args, **kwargs)
            return wrapped
        return decorator 
    
    # Interface
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
                jwt_header = self.get_auth_header(*args, **kwargs)
                user, enabled, strict = self.get_auth_arguments(jwt_header, self._enabled_default, self._strict_default, **kwargs)
                return self._dnr_client.execute_if_authenticated(user, enabled, strict, func, *args, **kwargs)
            return wrapped
        return decorator

    def _change_roles(self, action, roles, resource_id, **kwargs):
        if 'deathnut_calling_user' not in kwargs:
            logger.warn('Unauthenticated user attempt to update roles')
            return
        user = kwargs.get('deathnut_user', '')
        if roles:
            for role in roles:
                action(user, role, resource_id)

    def assign_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._dnr_client.assign_role, roles, resource_id, **kwargs)
    
    def revoke_roles(self, resource_id, roles, **kwargs):
        return self._change_roles(self._dnr_client.revoke_role, roles, resource_id, **kwargs)

    def create_auth_endpoint(self, name, requires_role, grants_role):
        test = self
        class DeathnutAuth:
            @self.requires_role(requires_role, strict=True)
            def on_post(self, **kwargs):
                dn_auth = request.json
                id = dn_auth['id']
                user = dn_auth['user']
                revoke = dn_auth.get('revoke', False)
                kwargs.update(deathnut_user=user)
                if revoke:
                    test.revoke_roles(id, [grants_role], **kwargs)
                else:
                    test.assign_roles(id, [grants_role], **kwargs)
                return {"id": id, "user": user, "role": grants_role, "revoke": revoke}, 200
        curr_auth_endpoint = DeathnutAuth()
        self._app.add_route(name, curr_auth_endpoint)