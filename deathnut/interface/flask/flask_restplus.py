from deathnut.interface.flask.flask_base import FlaskAuthorization
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.util.logger import get_deathnut_logger
from deathnut.util.redis import get_redis_connection
from deathnut.schema.restplus.dn_schemas_restplus import register_restplus_schemas
from flask import request
from flask_restplus import Resource

logger = get_deathnut_logger(__name__)

class FlaskRestplusAuthorization(FlaskAuthorization):
    def __init__(self, api, service, resource_type=None, strict=True, enabled=True, **kwargs):
        redis = get_redis_connection(**kwargs)
        super(FlaskRestplusAuthorization, self).__init__(service,resource_type=resource_type,
            strict=strict, enabled=enabled, redis_connection=redis)
        self.me = self
        self.ns = api.namespace("", description="Deathnut auth")
        self.deathnut_auth_schema, self.deathnut_error_schema = register_restplus_schemas(api)
        self.register_error_handler()
        api.add_namespace(self.ns)

    def create_auth_endpoint(self, name, requires_role, grants_role):
        test = self
        # @self.ns.route(name)
        class DeathnutAuth(Resource):
            @self.ns.expect(self.deathnut_auth_schema)
            @self.ns.marshal_with(self.deathnut_auth_schema)
            @self.requires_role(requires_role, strict=True)
            def post(self, **kwargs):
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
        # DeathnutAuth()
        # self.api.add_namespace(self.ns)
        # self.api.add_resource(DeathnutAuth)
        self.ns.add_resource(DeathnutAuth, name)

    def register_error_handler(self):
        @self.ns.errorhandler(DeathnutException)
        @self.ns.marshal_with(self.deathnut_error_schema)
        def handle_deathnut_failures(error):
            return {"message": error.args[0]}, 401
