import base64
import functools
import json
import logging
import sys

from concurrent.futures import ThreadPoolExecutor

# from flask import request, jsonify
from functools import partial

from deathnut.client.rest_client import DeathnutRestClient

from deathnut.util.logger import get_deathnut_logger
from deathnut.util.deathnut_exception import DeathnutException

import falcon
from apispec import APISpec

logger = get_deathnut_logger(__name__)


class ErrorHandler:
    @staticmethod
    def deathnut_exception(ex, req, resp, params):
        resp.media = {"message": ex.args[0]}
        resp.status = falcon.HTTP_401


class FalconAuthorization(object):
    def __init__(
        self,
        app,
        service,
        resource_type=None,
        strict=True,
        enabled=True,
        redis_connection=None,
    ):
        self._app = app
        self._dnr_client = DeathnutClient(
            service, resource_type, redis_connection=redis_connection
        )
        self._app.add_error_handler(DeathnutException, ErrorHandler.deathnut_exception)

    """Base class containing flask-specific logic"""

    @staticmethod
    def get_auth_header(*args, **kwargs):
        req = args[1]
        return req.get_header("X-Endpoint-Api-Userinfo", default="")

    @staticmethod
    def get_resource_id(*args, **kwargs):
        req = args[1]
        dn_args = req.media
        dn_args.update(kwargs)
        return dn_args

    @staticmethod
    def get_dont_wait(*args, **kwargs):
        # req = locals()['req']
        req = args[1]
        return kwargs.get("dont_wait", req.method == "GET")

    def create_auth_endpoint(self, name, requires_role, grants_role):
        test = self

        class DeathnutAuth:
            @self.requires_role(requires_role, strict=True)
            def on_post(self, **kwargs):
                dn_auth = request.json
                id = dn_auth["id"]
                user = dn_auth["user"]
                revoke = dn_auth.get("revoke", False)
                kwargs.update(deathnut_user=user)
                if revoke:
                    test.revoke_roles(id, [grants_role], **kwargs)
                else:
                    test.assign_roles(id, [grants_role], **kwargs)
                return (
                    {"id": id, "user": user, "role": grants_role, "revoke": revoke},
                    200,
                )

        curr_auth_endpoint = DeathnutAuth()
        self._app.add_route(name, curr_auth_endpoint)
