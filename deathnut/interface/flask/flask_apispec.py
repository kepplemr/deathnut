from flask import request, jsonify
from flask_apispec import marshal_with, use_kwargs
from marshmallow import Schema, fields

from deathnut.util.redis import get_redis_connection
from deathnut.util.deathnut_exception import DeathnutException
from .flask_base import FlaskAuthorization

class DeathnutAuthSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Resource id', required=True)
    user = fields.String(description='User to assign role to', required=True)
    role = fields.String(description='The role being assigned', required=True)

class FlaskAPISpecAuthorization(FlaskAuthorization):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, **kwargs):
        redis = get_redis_connection(**kwargs)
        super(FlaskAPISpecAuthorization, self).__init__(service, resource_type=resource_type, 
            strict=strict, enabled=enabled, redis_connection=redis)
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
        @self._app.route(name, methods=('POST',))
        @use_kwargs(DeathnutAuthSchema)
        @marshal_with(DeathnutAuthSchema)
        @self.requires_role(requires_role, strict=True)
        def auth(id, user, role, **kwargs):
            self.assign_roles(id, [role], deathnut_user=user)
            return {"id": id, "user": user, "role": role}, 200
        return auth

    def register_error_handler(self):
        @self._app.errorhandler(DeathnutException)
        #@api.marshal_with(error_fields, code=400)
        #@api.header('My-Header',  'Some description')
        def handle_fake_exception_with_header(error):
            '''This is a custom error'''
            return jsonify({'message': error.args[0]}), 401