from flask import request
from flask_restplus import Api, Resource, fields

from deathnut.util.redis import get_redis_connection
from deathnut.util.deathnut_exception import DeathnutException
from deathnut.interface.flask.flask_base import FlaskAuthorization

from deathnut.util.logger import get_deathnut_logger

logger = get_deathnut_logger(__name__)

#api = Api()
# ns = api.namespace('', description='Deathnut auth')



class FlaskRestplusAuthorization(FlaskAuthorization):
    def __init__(self, api, service, resource_type=None, strict=True, enabled=True, **kwargs):
        redis = get_redis_connection(**kwargs)
        super(FlaskRestplusAuthorization, self).__init__(service, resource_type=resource_type, 
            strict=strict, enabled=enabled, redis_connection=redis)
        self.api = api
        self.deathnut_auth_schema = api.model('DeathnutAuthSchema', {
            'id': fields.String(description='Resource id', required=True),
            'user': fields.String(description='User to assign role to', required=True),
            'role': fields.String(description='The role to assign or revoke', required=True),
            'revoke': fields.Boolean(description='If true, revokes the privilege')})
        self.deathnut_error_schema = api.model('DeathnutErrorSchema', {
            'message': fields.String(description='Description of what failed')})
        self.ns = self.api.namespace('', description='Deathnut auth')
        self.register_error_handler()
        #api.add_namespace(self.ns)

    def create_auth_endpoint(self, name, requires_role, grants_role):
        #@self.ns.route(name)
        class DeathnutAuth(Resource):
            @self.ns.expect(self.deathnut_auth_schema)
            @self.ns.marshal_with(self.deathnut_auth_schema)
            @self.requires_role(requires_role, strict=True)
            def post(self, **kwargs):
                dn_auth = request.json
                id = dn_auth['id']
                user = dn_auth['user']
                grants_role = dn_auth['grants_role']
                revoke = dn_auth.get('revoke', False)
                kwargs.update(deathnut_user=user)
                if revoke:
                    super.revoke_roles(id, [grants_role], **kwargs)
                else:
                    super.assign_roles(id, [grants_role], **kwargs)
                return {"id": id, "user": user, "role": grants_role, "revoke": revoke}, 200
        # DeathnutAuth()
        # self.api.add_namespace(self.ns)
        # self.api.add_resource(DeathnutAuth)
        self.ns.add_resource(DeathnutAuth, name)

    def register_error_handler(self):
        @self.ns.errorhandler(DeathnutException)
        @self.ns.marshal_with(self.deathnut_error_schema)
        def handle_deathnut_failures(error):
            return {'special error handler': error.args[0]}, 401