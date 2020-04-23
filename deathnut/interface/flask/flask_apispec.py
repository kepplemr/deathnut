from deathnut.interface.base_auth_endpoint import BaseAuthEndpoint
from deathnut.interface.flask.flask_base import FlaskAuthorization
from deathnut.schema.marshmallow.dn_schemas_marshmallow import (
    DeathnutAuthSchema, DeathnutErrorSchema)
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.jwt import get_user_from_jwt_header
from deathnut.util.logger import get_deathnut_logger
from flask_apispec import marshal_with, use_kwargs

logger = get_deathnut_logger(__name__)

class FlaskAPISpecAuthorization(FlaskAuthorization):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FlaskAPISpecAuthorization, self).__init__(service, resource_type=resource_type,
            strict=strict, enabled=enabled, **kwargs)
        self._app = app
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
        return FlaskAPISpecAuthEndpoint(self, self._app, name)

    def register_error_handler(self):
        @self._app.errorhandler(DeathnutException)
        @marshal_with(DeathnutErrorSchema)
        def handle_deathnut_failures(error):
            return {"message": error.args[0]}, 401

class FlaskAPISpecAuthEndpoint(BaseAuthEndpoint):
    def __init__(self, auth_o, app, name):
        self._app = app
        super(FlaskAPISpecAuthEndpoint, self).__init__(auth_o, name)

    def generate_auth_endpoint(self):
        @self._app.route(self._name, methods=("POST",))
        @use_kwargs(DeathnutAuthSchema, required=True)
        @marshal_with(DeathnutAuthSchema)
        @self._auth_o.authentication_required(strict=True)
        def auth(id, user, requires, grants, revoke=False, **kwargs):
            calling_user = kwargs.get('deathnut_user', 'Unauthenticated')
            if not self._auth_o.get_client().check_role(calling_user, requires, id):
                raise DeathnutException('Unauthorized to grant')
            # make sure the granting user has access to grant all roles.
            for role in grants:
                self.check_grant_enabled(requires, role)
            kwargs.update(deathnut_user=user)
            if revoke:
                self._auth_o.revoke_roles(id, grants, **kwargs)
            else:
                self._auth_o.assign_roles(id, grants, **kwargs)
            return {"id": id, "user": user, "requires": requires, "grants": grants, "revoke": revoke}, 200
        return auth
