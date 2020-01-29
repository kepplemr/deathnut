from abc import ABC

from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.util.logger import get_deathnut_logger
from flask import request

logger = get_deathnut_logger(__name__)

class FlaskAuthorization(BaseAuthorizationInterface, ABC):
    """Base class containing flask-specific logic"""
    def __init__(self, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FlaskAuthorization, self).__init__(service, resource_type, strict, enabled, **kwargs)

    @staticmethod
    def get_auth_header(*args, **kwargs):
        return request.headers.get('X-Endpoint-Api-Userinfo', '')

    @staticmethod
    def get_resource_id(id_identifier, *args, **kwargs):
        dn_args = request.view_args
        if request.json:
            dn_args.update(request.json)
        return dn_args[id_identifier]

    @staticmethod
    def get_dont_wait(*args, **kwargs):
        return kwargs.get('dont_wait', request.method == 'GET')
