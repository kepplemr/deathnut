from deathnut.interface.flask.flask_base import FlaskAuthorization
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.redis import get_redis_connection
from flask_apispec import marshal_with, use_kwargs
from marshmallow import Schema, fields

logger = get_deathnut_logger(__name__)

class DeathnutAuthSchema(Schema):
    class Meta:
        strict = True
    id = fields.String(description="Resource id", required=True)
    user = fields.String(description="User to assign role to", required=True)
    role = fields.String(description="The role to assign or revoke", required=False)
    revoke = fields.Boolean(description="If True, attempt to revoke the privilege", required=False)

class DeathnutErrorSchema(Schema):
    class Meta:
        strict = True
    message = fields.String(description="Description of what failed", required=True)

class FlaskAPISpecAuthorization(FlaskAuthorization):
    def __init__(
        self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        super(FlaskAPISpecAuthorization, self).__init__(service, resource_type=resource_type,
            strict=strict, enabled=enabled, **kwargs)
        self._app = app
        self.register_error_handler()

    def create_auth_endpoint(self, name, requires_role, grants_role):
        """
        Utility function to create an endpoint to grant privileges to other users. The endpoint
        will be strict by default (unauthenticated users not allowed).

        Parameters
        ----------
        name: str
            name of the endpoint to create, ex: '/auth-recipe'
        requires_role: str
            name of the role required of the calling user in order to grant privileges
        grants_role: str
            name of the role granted to the id if the calling user has the authority to do so.
        """
        @self._app.route(name, methods=("POST",))
        @use_kwargs(DeathnutAuthSchema)
        @marshal_with(DeathnutAuthSchema)
        @self.requires_role(requires_role, strict=True)
        def auth(id, user, revoke=False, **kwargs):
            kwargs.update(deathnut_user=user)
            if revoke:
                self.revoke_roles(id, [grants_role], **kwargs)
            else:
                self.assign_roles(id, [grants_role], **kwargs)
            return {"id": id, "user": user, "role": grants_role, "revoke": revoke}, 200
        return auth

    def register_error_handler(self):
        @self._app.errorhandler(DeathnutException)
        @marshal_with(DeathnutErrorSchema)
        def handle_deathnut_failures(error):
            return {"message": error.args[0]}, 401
