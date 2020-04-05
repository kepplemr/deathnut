import asyncio
import functools

from deathnut.interface.base_auth_endpoint import BaseAuthEndpoint
from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.schema.pydantic.dn_schemas_pydantic import DeathnutAuthSchema
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = get_deathnut_logger(__name__)

class FastapiAuthorization(BaseAuthorizationInterface):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FastapiAuthorization, self).__init__(service, resource_type, strict, enabled, **kwargs)
        self._app = app
        self.register_error_handler()

    def register_error_handler(self):
        @self._app.exception_handler(DeathnutException)
        async def unicorn_exception_handler(request: Request, exc: DeathnutException):
            return JSONResponse(status_code=401, content={"message": exc.args[0]})

    @staticmethod
    def _execute(dn_func, request, *args, **kwargs):
        request.deathnut_calling_user = kwargs.pop('deathnut_calling_user', 'Unauthenticated')
        request.deathnut_user = kwargs.pop('deathnut_user', 'Unauthenticated')
        return asyncio.run(dn_func(*args, request=request, **kwargs))

    @staticmethod
    def get_auth_header(request, *args, **kwargs):
        return request.headers.get('X-Endpoint-Api-Userinfo', '')

    @staticmethod
    # TODO do we need to consider body here?
    def get_resource_id(id_identifier, request, *args, **kwargs):
        return request.path_params[id_identifier]

    def _execute_asynchronously(self, dn_func, dn_role, dn_rid, request, *args, **kwargs):
        loop = asyncio.new_event_loop()
        request.deathnut_calling_user = kwargs.pop('deathnut_calling_user', 'Unauthenticated')
        request.deathnut_user = kwargs.pop('deathnut_user', 'Unauthenticated')
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(asyncio.gather(loop.run_in_executor(None,
                                          functools.partial(self.is_authorized,
                                          request.deathnut_calling_user, dn_role, dn_rid)),
                                          dn_func(*args, request=request, **kwargs)))
        if results[0]:
            return results[1]
        raise DeathnutException("Not authorized")

    @staticmethod
    def get_dont_wait(request, *args, **kwargs):
        kwargs.get('dont_wait', None)
        return kwargs.get("dont_wait", request.method == "GET")

    def assign_roles(self, resource_id, roles, **kwargs):
        request = kwargs.get('request')
        dn_calling_user = kwargs.get('deathnut_calling_user', getattr(request, 'deathnut_calling_user', 'Unauthenticated'))
        dn_user = kwargs.get('deathnut_user', getattr(request, 'deathnut_user', 'Unauthenticated'))
        return super(FastapiAuthorization, self)._change_roles(self._client.assign_role, roles, resource_id,
            deathnut_calling_user=dn_calling_user, deathnut_user=dn_user)

    def revoke_roles(self, resource_id, roles, **kwargs):
        dn_calling_user = kwargs.get('deathnut_calling_user', kwargs['request'].deathnut_calling_user)
        dn_user = kwargs.get('deathnut_user', kwargs['request'].deathnut_user)
        return super(FastapiAuthorization, self)._change_roles(self._client.revoke_role, roles, resource_id,
            deathnut_calling_user=dn_calling_user, deathnut_user=dn_user)

    def create_auth_endpoint(self, name):
        """
        Utility function to create an endpoint to grant privileges to other users. The endpoint
        will be strict by default (unauthenticated users not allowed).

        Parameters
        ----------
        name: str
            name of the endpoint to create, ex: '/auth-recipe'
        """
        return FastapiAuthEndpoint(self, self._app, name)


class FastapiAuthEndpoint(BaseAuthEndpoint):
    def __init__(self, auth_o, app, name):
        self._app = app
        super(FastapiAuthEndpoint, self).__init__(auth_o, name)

    def generate_auth_endpoint(self):
        @self._app.post(self._name, response_model=DeathnutAuthSchema)
        @self._auth_o.authentication_required(strict=True)
        async def auth(deathnutAuth: DeathnutAuthSchema, request: Request):
            calling_user = get_user_from_jwt_header(self._auth_o.get_auth_header(request))
            if not self._auth_o.get_client().check_role(calling_user, deathnutAuth.requires, deathnutAuth.id):
                raise DeathnutException('Unauthorized to grant')
            # make sure the granting user has access to grant all roles.
            for role in deathnutAuth.grants:
                self._check_grant_enabled(deathnutAuth.requires, role)
            if deathnutAuth.revoke:
                self._auth_o.revoke_roles(deathnutAuth.id, deathnutAuth.grants, deathnut_user=deathnutAuth.user, request=request)
            else:
                self._auth_o.assign_roles(deathnutAuth.id, deathnutAuth.grants, deathnut_user=deathnutAuth.user, request=request)
            return {"id": deathnutAuth.id, "user": deathnutAuth.user, "requires": deathnutAuth.requires,
                    "grants": deathnutAuth.grants, "revoke": deathnutAuth.revoke}
        return auth
