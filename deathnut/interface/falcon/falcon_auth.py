import falcon
from deathnut.interface.base_auth_endpoint import BaseAuthEndpoint
from deathnut.interface.base_interface import BaseAuthorizationInterface
from deathnut.schema.marshmallow.dn_schemas_marshmallow import \
    DeathnutAuthSchema
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from redis.exceptions import ConnectionError

logger = get_deathnut_logger(__name__)

class ErrorHandler:
    @staticmethod
    def deathnut_exception(ex, req, resp, params):
        resp.media = {"message": ex.args[0]}
        resp.status = falcon.HTTP_401
    @staticmethod
    def redis_exception(ex, req, resp, params):
        resp.media = {"message": "could not connect to redis"}
        resp.status = falcon.HTTP_500

class FalconAuthorization(BaseAuthorizationInterface):
    def __init__(self, app, spec, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FalconAuthorization, self).__init__(service, resource_type, strict, enabled, **kwargs)
        self._app = app
        self._spec = spec
        self._app.add_error_handler(DeathnutException, ErrorHandler.deathnut_exception)
        self._app.add_error_handler(ConnectionError, ErrorHandler.redis_exception)

    @staticmethod
    def get_auth_header(*args, **kwargs):
        req = args[1]
        return req.get_header("X-Endpoint-Api-Userinfo", default="")

    @staticmethod
    def get_body_response(ret, *args, **kwargs):
        return args[2].media

    @staticmethod
    def get_resource_id(id_identifier, *args, **kwargs):
        req = args[1]
        dn_args = req.media or {}
        dn_args.update(kwargs)
        return dn_args[id_identifier]

    @staticmethod
    def get_dont_wait(*args, **kwargs):
        req = args[1]
        return kwargs.get("dont_wait", req.method == "GET")

    def create_auth_endpoint(self, name):
        return FalconAuthEndpoint(self, self._app, self._spec, name)

class FalconAuthEndpoint(BaseAuthEndpoint):
    def __init__(self, auth_o, app, spec, name):
        self._auth_o = auth_o
        self._app = app
        self._spec = spec
        self._name = name
        super(FalconAuthEndpoint, self).__init__(auth_o, name)

    def generate_auth_endpoint(self):
        auth_o = self._auth_o
        endpoint = self
        class DeathnutAuth:
            @auth_o.authentication_required(strict=True)
            def on_post(self, req, resp, **kwargs):
                """
                Auth POST endpoint
                ---
                operationId: auth_endpoint
                parameters:
                - in: body
                  required: true
                  name: payload
                  schema: DeathnutAuthSchema
                responses:
                  200:
                    description: the granted/revoked access
                    schema: DeathnutAuthSchema
                """
                dn_auth = req.media
                id = dn_auth["id"]
                user = dn_auth["user"]
                requires = dn_auth["requires"]
                grants = dn_auth["grants"]
                revoke = dn_auth.get("revoke", False)
                calling_user = kwargs.get("deathnut_user", "Unauthenticated")
                if not auth_o.get_client().check_role(calling_user, requires, id):
                    raise DeathnutException('Unauthorized to grant')
                # make sure the granting user has access to grant all roles.
                for role in grants:
                    endpoint.check_grant_enabled(requires, role)
                kwargs.update(deathnut_user=user)
                if revoke:
                    auth_o.revoke_roles(id, grants, **kwargs)
                else:
                    auth_o.assign_roles(id, grants, **kwargs)
                resp.media = {"id": id, "user": user, "requires": requires, "grants": grants, "revoke": revoke}
                resp.status = falcon.HTTP_200
        curr_auth_endpoint = DeathnutAuth()
        self._app.add_route(self._name, curr_auth_endpoint)
        self._spec.components.schema("DeathnutAuthSchema", schema=DeathnutAuthSchema)
        self._spec.path(resource=curr_auth_endpoint)
