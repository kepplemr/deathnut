from deathnut.interface.base_auth_endpoint import BaseAuthEndpoint
from deathnut.interface.flask.flask_base import FlaskAuthorization
from deathnut.schema.restplus.dn_schemas_restplus import \
    register_restplus_schemas
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.redis import get_redis_connection
from flask import request
from flask_restplus import Resource

logger = get_deathnut_logger(__name__)

class FlaskRestplusAuthorization(FlaskAuthorization):
    def __init__(self, api, service, resource_type=None, strict=True, enabled=True, **kwargs):
        redis = get_redis_connection(**kwargs)
        super(FlaskRestplusAuthorization, self).__init__(service,resource_type=resource_type,
            strict=strict, enabled=enabled, redis_connection=redis)
        self._api = api
        self.deathnut_auth_schema, self.deathnut_error_schema = register_restplus_schemas(api)
        self.register_error_handler()

    def create_auth_endpoint(self, name):
        """
        Utility function to create an endpoint to grant privileges to other users. The endpoint
        will be strict by default (unauthenticated users not allowed).

        Parameters
        ----------
        name: str
            name of the endpoint to create, ex: '/auth-recipe'
        """
        return FlaskRestplusAuthEndpoint(self, self._api, name)

    def register_error_handler(self):
        @self._api.errorhandler(DeathnutException)
        @self._api.marshal_with(self.deathnut_error_schema)
        def handle_deathnut_failures(error):
            """Returns error message encountered"""
            return {"message": error.args[0]}, 401

class FlaskRestplusAuthEndpoint(BaseAuthEndpoint):
    def __init__(self, auth_o, api, name):
        self._api = api
        self._ns = self._api.namespace("", description="Deathnut auth")
        super(FlaskRestplusAuthEndpoint, self).__init__(auth_o, name)
        self._api.add_namespace(self._ns)

    def generate_auth_endpoint(self):
        interface = self
        class DeathnutAuth(Resource):
            @interface._ns.expect(interface._auth_o.deathnut_auth_schema)
            @interface._ns.marshal_with(interface._auth_o.deathnut_auth_schema)
            @interface._auth_o.authentication_required(strict=True)
            def post(self, **kwargs):
                dn_auth = request.json
                id = dn_auth["id"]
                user = dn_auth["user"]
                requires = dn_auth["requires"]
                grants = dn_auth["grants"]
                revoke = dn_auth.get("revoke", False)
                calling_user = get_user_from_jwt_header(interface._auth_o.get_auth_header())
                if not interface._auth_o.get_client().check_role(calling_user, requires, id):
                    raise DeathnutException('Unauthorized to grant')
                # make sure the granting user has access to grant all roles.
                for role in grants:
                    interface._check_grant_enabled(requires, role)
                kwargs.update(deathnut_user=user)
                if revoke:
                    interface._auth_o.revoke_roles(id, grants, **kwargs)
                else:
                    interface._auth_o.assign_roles(id, grants, **kwargs)
                return {"id": id, "user": user, "requires": requires, "grants": grants, "revoke": revoke}, 200
        self._ns.add_resource(DeathnutAuth, self._name)
