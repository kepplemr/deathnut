from flask import request, jsonify
from flask_apispec import marshal_with, use_kwargs
from marshmallow import Schema, fields

from deathnut.util.deathnut_exception import DeathnutException
from .flask_base import FlaskAuthorization

class DeathnutAuthSchema(Schema):
    class Meta:
        strict = True
    id = fields.Integer(description='Resource id', required=True)
    user = fields.String(description='User to assign role to', required=True)
    role = fields.String(description='The role being assigned', required=True)

class FlaskAPISpecAuthorization(FlaskAuthorization):
    def __init__(self, app, service, resource_type=None, strict=True, enabled=True, 
            redis_connection=None, redis_host='redis', redis_port=6379, redis_pw=None, redis_db=0):
        super(FlaskAPISpecAuthorization, self).__init__(service, resource_type, redis_connection, redis_host, redis_port, redis_pw, redis_db)
        self._app = app
        self.register_error_handler()

    def create_auth_endpoint(self, name, requires_role, grants_role):
        @self._app.route(name, methods=('POST',))
        @use_kwargs(DeathnutAuthSchema)
        @marshal_with(DeathnutAuthSchema)
        @self.requires_role('own')
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