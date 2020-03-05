from fastapi import FastAPI, Header
from starlette.requests import Request

import asyncio

from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)

class FastapiAuthorization(BaseAuthorizationInterface):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FastapiAuthorization, self).__init__(service, resource_type, strict, enabled, **kwargs)
        self._app = app
        self.register_middleware()


    def _deathnut_checks_successful(self, dn_user, dn_func, request, *args, **kwargs):
        request.deathnut_calling_user = dn_user
        request.deathnut_user = dn_user
        return asyncio.run(dn_func(*args, request=request, **kwargs))

    
    @staticmethod
    def get_auth_header(request, *args, **kwargs):
        return request.headers.get('X-Endpoint-Api-Userinfo', '')
    
    def register_middleware(self):
        @self._app.middleware("http")
        async def add_process_time_header(request: Request, call_next):
            # logger.info('Hey here')
            # logger.info('Request -> ' + str(request))
            logger.info('Request dir -> ' + str(dir(request)))
            # logger.info('Request headers -> ' + str(request.headers))
            response = await call_next(request)
            #response.headers["X-Process-Time"] = str(process_time)
            return response


    @staticmethod
    def get_resource_id(id_identifier, request, *args, **kwargs):
        return request.path_params[id_identifier]


    @staticmethod
    def get_dont_wait(request, *args, **kwargs):
        dont_wait = kwargs.get('dont_wait', None)
        logger.warn('Dont wait KW val -> ' + str(dont_wait))
        logger.warn('Request method -> ' + str(request.method))
        return kwargs.get("dont_wait", request.method == "GET")


    def create_auth_endpoint(self, name, requires_role, grants_role):
        pass

    def assign_roles(self, resource_id, roles, **kwargs):
        dn_calling_user = kwargs.get('deathnut_calling_user', kwargs['request'].deathnut_calling_user)
        dn_user = kwargs.get('deathnut_user', kwargs['request'].deathnut_user)
        return super(FastapiAuthorization, self)._change_roles(self._client.assign_role, roles, resource_id, 
            deathnut_calling_user=dn_calling_user, deathnut_user=dn_user)

    def revoke_roles(self, resource_id, roles, **kwargs):
        dn_calling_user = kwargs.get('deathnut_calling_user', kwargs['request'].deathnut_calling_user)
        dn_user = kwargs.get('deathnut_user', kwargs['request'].deathnut_user)
        return super(FastapiAuthorization, self)._change_roles(self._client.assign_role, roles, resource_id, 
            deathnut_calling_user=dn_calling_user, deathnut_user=dn_user)